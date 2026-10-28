"""Núcleo del Worker de Adjudicación SAOM · Proyecto COIL (Sistema de Salud de Chernovia).

Implementa los 8 componentes de C4 Nivel 3 definidos en `design/03_arquitectura_tecnica.md`:
1. ParticionadorCSV: Divide archivos CSV en descriptores de rangos de bytes de 5.000 filas.
2. LectorValidador: Lee un rango de bytes y valida el esquema de cada solicitud (RF-01).
3. Pseudonimizador: Calcula `patient_token` con HMAC-SHA256 y enmascara PII con `#` conservando longitud (RF-02, RNF-05).
4. ExtractorClinico: Extrae Edad, PerfilCobertura, ServicioSolicitado y Medicacion con spans `[start, end]` (RF-02, RNF-02).
5. ResolutorPerfil: Mapea PRIORITARIO (100%), ESTANDAR (50%), COPAGO (25%) desde el catálogo oficial (RF-04).
6. MotorCobertura: Evalúa cobertura contra `COIL_catalogo_servicios_cubiertos.csv` (COV-001..COV-020) (RF-03).
7. LiquidadorFinanciero: Calcula `valor_aprobado` y `valor_copago` con `Decimal` y `ROUND_HALF_UP` (RF-04).
8. GeneradorRecibo: Firma cada decisión sobre JSON canónico (SHA-256) y construye la raíz hash del chunk y del lote (RF-05, RNF-04).
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CATALOGO_VERSION_DEFAULT = "COIL-2026.1"
MODELO_VERSION_DEFAULT = "coil-ner-lex-v1.0"
CENTAVO = Decimal("0.01")
CIEN = Decimal("100")

# Expresión regular compilada para extraer campos y sus posiciones exactas (spans) en la glosa COIL
REGEX_CAMPO_GLOSA = re.compile(
    r"(Paciente|DNO|SeguroSocial|Edad|PerfilCobertura|ServicioSolicitado|Medicacion):\s*([^;]+)"
)


@dataclass(frozen=True)
class ServicioCatalogo:
    codigo_servicio: str
    servicio: str
    categoria: str
    medicaciones_referencia: frozenset[str]
    valor_min_referencia: Decimal
    valor_max_referencia: Decimal
    cubre_sistema_publico: bool


class CatalogoCOIL:
    """Mantiene en memoria los catálogos normativos oficiales de Chernovia (`saom-ref`)."""

    def __init__(
        self,
        servicios_path: Path | str,
        perfiles_path: Path | str,
        version: str = CATALOGO_VERSION_DEFAULT,
    ) -> None:
        self.version = version
        self.servicios: Dict[str, ServicioCatalogo] = {}
        self.perfiles: Dict[str, int] = {}
        self._cargar_servicios(Path(servicios_path))
        self._cargar_perfiles(Path(perfiles_path))

    def _cargar_servicios(self, path: Path) -> None:
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                nombre = row["servicio"].strip()
                meds_raw = row["medicaciones_referencia"].strip()
                meds = (
                    frozenset()
                    if meds_raw.lower() == "ninguna"
                    else frozenset(m.strip().lower() for m in meds_raw.split("|") if m.strip())
                )
                self.servicios[nombre] = ServicioCatalogo(
                    codigo_servicio=row["codigo_servicio"].strip(),
                    servicio=nombre,
                    categoria=row["categoria"].strip(),
                    medicaciones_referencia=meds,
                    valor_min_referencia=Decimal(row["valor_min_referencia"].strip()),
                    valor_max_referencia=Decimal(row["valor_max_referencia"].strip()),
                    cubre_sistema_publico=row["cubre_sistema_publico"].strip().upper() == "SI",
                )

    def _cargar_perfiles(self, path: Path) -> None:
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                perfil = row["perfil_cobertura"].strip().upper()
                porcentaje = int(row["porcentaje_cobertura_si_el_servicio_esta_cubierto"].strip())
                self.perfiles[perfil] = porcentaje


@dataclass(frozen=True)
class DescriptorChunk:
    lote_id: str
    chunk_id: int
    byte_inicio: int
    byte_fin: int
    num_ordenes: int


@dataclass
class EntidadesExtraidas:
    paciente_span: Tuple[int, int]
    dno: str
    dno_span: Tuple[int, int]
    seguro_social: str
    seguro_social_span: Tuple[int, int]
    edad: Optional[int]
    edad_span: Optional[Tuple[int, int]]
    perfil_cobertura: str
    perfil_span: Optional[Tuple[int, int]]
    servicio_solicitado: str
    servicio_span: Optional[Tuple[int, int]]
    medicaciones: List[Tuple[str, int, int]]
    medicacion_span: Optional[Tuple[int, int]]
    confianza: float
    flags: List[str] = field(default_factory=list)


@dataclass
class DecisionAdjudicacion:
    id_solicitud: str
    lote_id: str
    chunk_id: int
    fecha_solicitud: str
    medio_emisor: str
    entidad_emisora: str
    patient_token: str
    glosa_enmascarada: str
    edad: int
    perfil_cobertura: str
    servicio_solicitado: str
    codigo_servicio: str
    categoria_servicio: str
    medicaciones: List[Dict[str, object]]
    spans: Dict[str, List[int]]
    dictamen: str
    causal_glosa: str
    regla_ids: List[str]
    catalogo_version: str
    modelo_version: str
    porcentaje: int
    valor_procedimiento: Decimal
    valor_aprobado: Decimal
    valor_copago: Decimal
    confianza: float
    flags: List[str]
    hash_decision: str

    def to_canonical_dict(self) -> Dict[str, object]:
        """Construye el diccionario determinista para el JSON canónico del hash (sección 7.4)."""
        return {
            "catalogo_version": self.catalogo_version,
            "dictamen": self.dictamen,
            "id_solicitud": self.id_solicitud,
            "modelo_version": self.modelo_version,
            "patient_token": self.patient_token,
            "perfil_cobertura": self.perfil_cobertura,
            "porcentaje": self.porcentaje,
            "regla_ids": sorted(self.regla_ids),
            "spans": {k: list(v) for k, v in sorted(self.spans.items())},
            "valor_aprobado": f"{self.valor_aprobado:.2f}",
            "valor_procedimiento": f"{self.valor_procedimiento:.2f}",
        }


@dataclass
class RechazoSintaxis:
    lote_id: str
    chunk_id: int
    linea_num: int
    id_solicitud: str
    estado: str
    motivo: str


@dataclass
class ResultadoChunk:
    lote_id: str
    chunk_id: int
    ordenes_validas: int
    ordenes_rechazadas: int
    ordenes_cubiertas: int
    ordenes_no_cubiertas: int
    ordenes_incertidumbre: int
    suma_reclamada: Decimal
    suma_aprobada: Decimal
    raiz_hash_chunk: str
    decisiones: List[DecisionAdjudicacion]
    rechazos: List[RechazoSintaxis]


COLUMNAS_ESPERADAS = [
    "id_solicitud",
    "fecha_solicitud",
    "glosa",
    "medio_emisor",
    "valor_procedimiento",
    "entidad_emisora",
]


def particionar_csv_en_chunks(
    csv_path: Path | str,
    lote_id: str,
    tamano_chunk: int = 5000,
) -> List[DescriptorChunk]:
    """Valida la cabecera CSV y calcula los desplazamientos en bytes de cada bloque de `tamano_chunk` filas."""
    path = Path(csv_path)
    descriptores: List[DescriptorChunk] = []
    with open(path, mode="rb") as f:
        header_bytes = f.readline()
        if not header_bytes:
            raise ValueError("Archivo CSV vacío")
        header_str = header_bytes.decode("utf-8-sig").strip()
        cols = [c.strip() for c in header_str.split(",")]
        if cols != COLUMNAS_ESPERADAS:
            raise ValueError(f"Cabecera CSV inválida: {cols}. Se esperaba: {COLUMNAS_ESPERADAS}")

        chunk_id = 0
        byte_inicio = f.tell()
        conteo = 0
        while True:
            linea = f.readline()
            if not linea:
                if conteo > 0:
                    byte_fin = f.tell() - 1
                    descriptores.append(
                        DescriptorChunk(
                            lote_id=lote_id,
                            chunk_id=chunk_id,
                            byte_inicio=byte_inicio,
                            byte_fin=byte_fin,
                            num_ordenes=conteo,
                        )
                    )
                break
            conteo += 1
            if conteo == tamano_chunk:
                byte_fin = f.tell() - 1
                descriptores.append(
                    DescriptorChunk(
                        lote_id=lote_id,
                        chunk_id=chunk_id,
                        byte_inicio=byte_inicio,
                        byte_fin=byte_fin,
                        num_ordenes=conteo,
                    )
                )
                chunk_id += 1
                byte_inicio = f.tell()
                conteo = 0

    return descriptores


def extraer_y_pseudonimizar_glosa(
    glosa: str,
    clave_hmac: bytes,
) -> Tuple[str, str, EntidadesExtraidas]:
    """Extrae las entidades con sus spans exactos y enmascara Paciente, DNO y SeguroSocial con `#`."""
    posiciones: Dict[str, Tuple[str, int, int]] = {}
    for match in REGEX_CAMPO_GLOSA.finditer(glosa):
        clave = match.group(1)
        valor = match.group(2).strip()
        inicio = match.start(2)
        fin = inicio + len(valor)
        posiciones[clave] = (valor, inicio, fin)

    flags: List[str] = []
    campos_requeridos = (
        "Paciente",
        "DNO",
        "SeguroSocial",
        "Edad",
        "PerfilCobertura",
        "ServicioSolicitado",
        "Medicacion",
    )
    presentes = sum(1 for c in campos_requeridos if c in posiciones)
    confianza = round(presentes / len(campos_requeridos), 4)

    dno_val, dno_ini, dno_fin = posiciones.get("DNO", ("", 0, 0))
    nss_val, nss_ini, nss_fin = posiciones.get("SeguroSocial", ("", 0, 0))
    pac_val, pac_ini, pac_fin = posiciones.get("Paciente", ("", 0, 0))

    if not dno_val or not nss_val or not pac_val:
        confianza = min(confianza, 0.50)
        flags.append("AUDIT_FLAG_CLINICAL_UNCERTAINTY")

    # Tokenización determinista HMAC-SHA256(clave_secreta, DNO || SeguroSocial)
    mensaje_hmac = f"{dno_val}||{nss_val}".encode("utf-8")
    patient_token = hmac.new(clave_hmac, mensaje_hmac, hashlib.sha256).hexdigest()

    # Enmascaramiento in-situ preservando exactamente la longitud de la glosa
    chars = list(glosa)
    for ini, fin in ((pac_ini, pac_fin), (dno_ini, dno_fin), (nss_ini, nss_fin)):
        for idx in range(ini, fin):
            chars[idx] = "#"
    glosa_enmascarada = "".join(chars)

    # Edad
    edad_val: Optional[int] = None
    edad_span: Optional[Tuple[int, int]] = None
    if "Edad" in posiciones:
        raw_edad, e_ini, e_fin = posiciones["Edad"]
        try:
            edad_val = int(raw_edad)
            edad_span = (e_ini, e_fin)
            if edad_val < 0 or edad_val > 125:
                flags.append("AUDIT_FLAG_CLINICAL_UNCERTAINTY")
                confianza = min(confianza, 0.65)
        except ValueError:
            flags.append("AUDIT_FLAG_CLINICAL_UNCERTAINTY")
            confianza = min(confianza, 0.60)
    else:
        flags.append("AUDIT_FLAG_CLINICAL_UNCERTAINTY")

    # Perfil de Cobertura
    perfil_val = ""
    perfil_span: Optional[Tuple[int, int]] = None
    if "PerfilCobertura" in posiciones:
        p_raw, p_ini, p_fin = posiciones["PerfilCobertura"]
        perfil_val = p_raw
        perfil_span = (p_ini, p_fin)

    # Servicio Solicitado
    servicio_val = ""
    servicio_span: Optional[Tuple[int, int]] = None
    if "ServicioSolicitado" in posiciones:
        s_raw, s_ini, s_fin = posiciones["ServicioSolicitado"]
        servicio_val = s_raw
        servicio_span = (s_ini, s_fin)
    else:
        flags.append("AUDIT_FLAG_CLINICAL_UNCERTAINTY")
        confianza = min(confianza, 0.50)

    # Medicaciones (separadas por |) con el span individual de cada medicamento
    medicaciones: List[Tuple[str, int, int]] = []
    med_span_global: Optional[Tuple[int, int]] = None
    if "Medicacion" in posiciones:
        m_raw, m_ini, m_fin = posiciones["Medicacion"]
        med_span_global = (m_ini, m_fin)
        cursor = m_ini
        for parte in m_raw.split("|"):
            med_limpio = parte.strip()
            offset_interno = parte.find(med_limpio)
            sub_ini = cursor + offset_interno
            sub_fin = sub_ini + len(med_limpio)
            if med_limpio:
                medicaciones.append((med_limpio, sub_ini, sub_fin))
            cursor += len(parte) + 1

    if confianza < 0.70 and "AUDIT_FLAG_CLINICAL_UNCERTAINTY" not in flags:
        flags.append("AUDIT_FLAG_CLINICAL_UNCERTAINTY")

    entidades = EntidadesExtraidas(
        paciente_span=(pac_ini, pac_fin),
        dno=dno_val,
        dno_span=(dno_ini, dno_fin),
        seguro_social=nss_val,
        seguro_social_span=(nss_ini, nss_fin),
        edad=edad_val,
        edad_span=edad_span,
        perfil_cobertura=perfil_val,
        perfil_span=perfil_span,
        servicio_solicitado=servicio_val,
        servicio_span=servicio_span,
        medicaciones=medicaciones,
        medicacion_span=med_span_global,
        confianza=confianza,
        flags=flags,
    )
    return patient_token, glosa_enmascarada, entidades


def calcular_hash_decision(decision_canonica: Dict[str, object]) -> str:
    """Calcula el SHA-256 sobre el JSON canónico (llaves ordenadas, sin espacios, UTF-8)."""
    canonico = json.dumps(
        decision_canonica,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def calcular_raiz_chunk(decisiones: List[DecisionAdjudicacion]) -> str:
    """Calcula la raíz hash del chunk concatenando los hashes ordenados por `id_solicitud`."""
    ordenadas = sorted(decisiones, key=lambda d: d.id_solicitud)
    concatenado = "".join(d.hash_decision for d in ordenadas)
    return hashlib.sha256(concatenado.encode("utf-8")).hexdigest()


def calcular_raiz_lote(raices_chunks: List[Tuple[int, str]]) -> str:
    """Calcula la raíz hash del lote concatenando las raíces de sus chunks en orden de `chunk_id`."""
    ordenadas = sorted(raices_chunks, key=lambda x: x[0])
    concatenado = "".join(h for _, h in ordenadas)
    return hashlib.sha256(concatenado.encode("utf-8")).hexdigest()


def verificar_integridad_orden(
    decision: DecisionAdjudicacion,
    recibo_worm_hash: str,
    decisiones_chunk: List[DecisionAdjudicacion],
    raiz_chunk_manifiesto: str,
) -> bool:
    """Verifica en tres pasos que una decisión no haya sido alterada (sección 7.4)."""
    hash_recalculado = calcular_hash_decision(decision.to_canonical_dict())
    if hash_recalculado != decision.hash_decision:
        return False
    if hash_recalculado != recibo_worm_hash:
        return False
    raiz_recalculada = calcular_raiz_chunk(decisiones_chunk)
    return raiz_recalculada == raiz_chunk_manifiesto


def adjudicar_fila_csv(
    campos: List[str],
    lote_id: str,
    chunk_id: int,
    linea_num: int,
    catalogo: CatalogoCOIL,
    clave_hmac: bytes,
    modelo_version: str = MODELO_VERSION_DEFAULT,
) -> Tuple[Optional[DecisionAdjudicacion], Optional[RechazoSintaxis]]:
    """Valida y adjudica una solicitud médica individual aplicando RF-01 a RF-05."""
    if len(campos) != 6:
        id_sol = campos[0].strip() if campos else f"LINEA-{linea_num}"
        return None, RechazoSintaxis(
            lote_id=lote_id,
            chunk_id=chunk_id,
            linea_num=linea_num,
            id_solicitud=id_sol,
            estado="REJECTED_SYNTAX",
            motivo=f"Número de columnas inválido ({len(campos)} en lugar de 6)",
        )

    id_solicitud, fecha_solicitud, glosa, medio_emisor, valor_raw, entidad_emisora = (
        c.strip() for c in campos
    )

    if not id_solicitud or not fecha_solicitud or not glosa or not medio_emisor or not entidad_emisora or not valor_raw:
        return None, RechazoSintaxis(
            lote_id=lote_id,
            chunk_id=chunk_id,
            linea_num=linea_num,
            id_solicitud=id_solicitud or f"LINEA-{linea_num}",
            estado="REJECTED_SYNTAX",
            motivo="Campo obligatorio vacío en la solicitud",
        )

    try:
        valor_procedimiento = Decimal(valor_raw).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        if valor_procedimiento <= Decimal("0.00"):
            raise InvalidOperation("Valor no positivo")
    except InvalidOperation:
        return None, RechazoSintaxis(
            lote_id=lote_id,
            chunk_id=chunk_id,
            linea_num=linea_num,
            id_solicitud=id_solicitud,
            estado="REJECTED_SYNTAX",
            motivo=f"valor_procedimiento inválido: '{valor_raw}'",
        )

    # RF-02: Pseudonimización y Extracción Clínica con spans
    patient_token, glosa_enmascarada, ent = extraer_y_pseudonimizar_glosa(glosa, clave_hmac)
    if not ent.dno or not ent.seguro_social:
        return None, RechazoSintaxis(
            lote_id=lote_id,
            chunk_id=chunk_id,
            linea_num=linea_num,
            id_solicitud=id_solicitud,
            estado="REJECTED_SYNTAX",
            motivo="Glosa sin identificadores DNO o SeguroSocial válidos",
        )

    flags = list(ent.flags)
    regla_ids: List[str] = []

    # RF-03: Dictamen de cobertura contra COIL_catalogo_servicios_cubiertos.csv
    servicio_info = catalogo.servicios.get(ent.servicio_solicitado)
    if servicio_info is not None and servicio_info.cubre_sistema_publico:
        dictamen = "CUBRE"
        codigo_servicio = servicio_info.codigo_servicio
        categoria_servicio = servicio_info.categoria
        causal_glosa = "SERVICIO_CUBIERTO_CATALOGO_OFICIAL"
        regla_ids.append(codigo_servicio)

        # Validaciones adicionales de auditoría sobre rango tarifario y medicación de referencia
        if not (servicio_info.valor_min_referencia <= valor_procedimiento <= servicio_info.valor_max_referencia):
            flags.append("AUDIT_FLAG_VALOR_FUERA_RANGO_REF")
        if servicio_info.medicaciones_referencia:
            meds_extraidas = {m[0].lower() for m in ent.medicaciones if m[0].lower() != "ninguna"}
            if not meds_extraidas.issubset(servicio_info.medicaciones_referencia):
                flags.append("AUDIT_FLAG_MEDICACION_NO_REFERENCIA")
    else:
        dictamen = "NO_CUBRE"
        codigo_servicio = "NO_CUBIERTO"
        categoria_servicio = "Excluido"
        causal_glosa = "GLOSA-EXCL-SERVICIO-NO-CUBIERTO"
        regla_ids.append("RULE-EXCL-NO-CATALOGADO")

    # RF-04: Resolución de perfil y liquidación financiera escalonada con Decimal(ROUND_HALF_UP)
    perfil_upper = ent.perfil_cobertura.upper()
    if dictamen == "CUBRE" and perfil_upper in catalogo.perfiles:
        porcentaje = catalogo.perfiles[perfil_upper]
        regla_ids.append(f"PERFIL-{perfil_upper}-{porcentaje}")
    else:
        porcentaje = 0
        if perfil_upper not in catalogo.perfiles:
            flags.append("AUDIT_FLAG_PERFIL_DESCONOCIDO")
            regla_ids.append("PERFIL-INVALIDO-0")
        else:
            regla_ids.append(f"PERFIL-{perfil_upper}-NO-CUBRE-0")

    valor_aprobado = (
        (valor_procedimiento * Decimal(porcentaje)) / CIEN
    ).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    valor_copago = (valor_procedimiento - valor_aprobado).quantize(CENTAVO, rounding=ROUND_HALF_UP)

    spans_dict: Dict[str, List[int]] = {}
    if ent.edad_span:
        spans_dict["Edad"] = [ent.edad_span[0], ent.edad_span[1]]
    if ent.perfil_span:
        spans_dict["PerfilCobertura"] = [ent.perfil_span[0], ent.perfil_span[1]]
    if ent.servicio_span:
        spans_dict["ServicioSolicitado"] = [ent.servicio_span[0], ent.servicio_span[1]]
    if ent.medicacion_span:
        spans_dict["Medicacion"] = [ent.medicacion_span[0], ent.medicacion_span[1]]

    meds_struct = [
        {"nombre": nombre, "span_inicio": ini, "span_fin": fin}
        for nombre, ini, fin in ent.medicaciones
    ]

    decision = DecisionAdjudicacion(
        id_solicitud=id_solicitud,
        lote_id=lote_id,
        chunk_id=chunk_id,
        fecha_solicitud=fecha_solicitud,
        medio_emisor=medio_emisor,
        entidad_emisora=entidad_emisora,
        patient_token=patient_token,
        glosa_enmascarada=glosa_enmascarada,
        edad=ent.edad if ent.edad is not None else -1,
        perfil_cobertura=perfil_upper,
        servicio_solicitado=ent.servicio_solicitado,
        codigo_servicio=codigo_servicio,
        categoria_servicio=categoria_servicio,
        medicaciones=meds_struct,
        spans=spans_dict,
        dictamen=dictamen,
        causal_glosa=causal_glosa,
        regla_ids=sorted(regla_ids),
        catalogo_version=catalogo.version,
        modelo_version=modelo_version,
        porcentaje=porcentaje,
        valor_procedimiento=valor_procedimiento,
        valor_aprobado=valor_aprobado,
        valor_copago=valor_copago,
        confianza=ent.confianza,
        flags=flags,
        hash_decision="",
    )
    decision.hash_decision = calcular_hash_decision(decision.to_canonical_dict())
    return decision, None


def procesar_rango_bytes_csv(
    bloque_bytes: bytes,
    descriptor: DescriptorChunk,
    catalogo: CatalogoCOIL,
    clave_hmac: bytes,
    modelo_version: str = MODELO_VERSION_DEFAULT,
    retener_decisiones: bool = True,
) -> ResultadoChunk:
    """Procesa un bloque de bytes CSV correspondiente a un chunk de hasta 5.000 órdenes."""
    texto = bloque_bytes.decode("utf-8")
    lector = csv.reader(io.StringIO(texto))

    decisiones: List[DecisionAdjudicacion] = []
    hashes_para_raiz: List[Tuple[str, str]] = []
    rechazos: List[RechazoSintaxis] = []

    ordenes_validas = 0
    ordenes_rechazadas = 0
    ordenes_cubiertas = 0
    ordenes_no_cubiertas = 0
    ordenes_incertidumbre = 0
    suma_reclamada = Decimal("0.00")
    suma_aprobada = Decimal("0.00")

    for idx, campos in enumerate(lector, start=1):
        if not campos or (len(campos) == 1 and not campos[0].strip()):
            continue
        decision, rechazo = adjudicar_fila_csv(
            campos=campos,
            lote_id=descriptor.lote_id,
            chunk_id=descriptor.chunk_id,
            linea_num=idx,
            catalogo=catalogo,
            clave_hmac=clave_hmac,
            modelo_version=modelo_version,
        )
        if rechazo is not None:
            ordenes_rechazadas += 1
            rechazos.append(rechazo)
            continue

        assert decision is not None
        ordenes_validas += 1
        if decision.dictamen == "CUBRE":
            ordenes_cubiertas += 1
        else:
            ordenes_no_cubiertas += 1
        if "AUDIT_FLAG_CLINICAL_UNCERTAINTY" in decision.flags:
            ordenes_incertidumbre += 1

        suma_reclamada += decision.valor_procedimiento
        suma_aprobada += decision.valor_aprobado
        hashes_para_raiz.append((decision.id_solicitud, decision.hash_decision))
        if retener_decisiones:
            decisiones.append(decision)

    hashes_para_raiz.sort(key=lambda x: x[0])
    concatenado = "".join(h for _, h in hashes_para_raiz)
    raiz_hash_chunk = hashlib.sha256(concatenado.encode("utf-8")).hexdigest()

    return ResultadoChunk(
        lote_id=descriptor.lote_id,
        chunk_id=descriptor.chunk_id,
        ordenes_validas=ordenes_validas,
        ordenes_rechazadas=ordenes_rechazadas,
        ordenes_cubiertas=ordenes_cubiertas,
        ordenes_no_cubiertas=ordenes_no_cubiertas,
        ordenes_incertidumbre=ordenes_incertidumbre,
        suma_reclamada=suma_reclamada,
        suma_aprobada=suma_aprobada,
        raiz_hash_chunk=raiz_hash_chunk,
        decisiones=decisiones,
        rechazos=rechazos,
    )
