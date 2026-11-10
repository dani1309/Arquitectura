"""Pruebas BDD de T1: un test por cada escenario de RF-01 a RF-05 y criterios de terminado del plan.

La escritura real en `rechazos/`, en el bucket WORM y en Parquet corresponde a T3. Aquí se verifica
el contenido que el núcleo entrega para esas salidas.
"""
from __future__ import annotations

import ast
import csv
import dataclasses
import hashlib
import io
import json
import re
import unittest
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import saom_core
from saom_core import (
    CatalogoCOIL,
    DescriptorChunk,
    adjudicar_fila_csv,
    calcular_hash_decision,
    calcular_raiz_chunk,
    calcular_raiz_lote,
    extraer_y_pseudonimizar_glosa,
    procesar_rango_bytes_csv,
    verificar_integridad_orden,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REF_DIR = REPO_ROOT / "data" / "ref"
CLAVE_SECRETA_TEST = b"coil-chernovia-secret-hmac-key-2026"

UNCERTAINTY = "AUDIT_FLAG_CLINICAL_UNCERTAINTY"
PERFIL_DESCONOCIDO = "AUDIT_FLAG_PERFIL_DESCONOCIDO"
FUERA_RANGO = "AUDIT_FLAG_VALOR_FUERA_RANGO_REF"
MED_NO_REF = "AUDIT_FLAG_MEDICACION_NO_REFERENCIA"

NOMBRE = "Paula Vargas Ramírez"
DNO = "DNO-23291911"
SS = "SS-173-47-2763"
MEDS_TERAPIA = "acetaminofén|diclofenaco tópico|naproxeno|ciclobenzaprina"
GLOSA_CHV1 = (
    f"Paciente: {NOMBRE}; DNO: {DNO}; SeguroSocial: {SS}; Edad: 14; PerfilCobertura: ESTANDAR; "
    f"ServicioSolicitado: Terapia física ambulatoria; Medicacion: {MEDS_TERAPIA}"
)
CASI_CUATRO = round(6 / 7, 4)


def glosa_coil(omitir: Iterable[str] = (), **valores: str) -> str:
    base: Dict[str, str] = {
        "Paciente": NOMBRE,
        "DNO": DNO,
        "SeguroSocial": SS,
        "Edad": "14",
        "PerfilCobertura": "ESTANDAR",
        "ServicioSolicitado": "Terapia física ambulatoria",
        "Medicacion": MEDS_TERAPIA,
    }
    base.update(valores)
    return "; ".join(f"{k}: {v}" for k, v in base.items() if k not in set(omitir))


def fila_coil(glosa: str, valor: str = "84617", id_solicitud: str = "CHV-0000001") -> List[str]:
    return [id_solicitud, "2026-05-06 10:09:31", glosa, "Farmacia Aliada", valor, "Unidad de Salud Valle Claro"]


def salida_a_texto(salida: object) -> str:
    return json.dumps(dataclasses.asdict(salida), ensure_ascii=False, default=str)


def coincidencias_pii(texto: str, nombres: Sequence[str]) -> List[str]:
    hallazgos = re.findall(r"DNO-\d+", texto) + re.findall(r"SS-\d{3}-\d{2}-\d{4}", texto)
    return hallazgos + [n for n in nombres if n in texto]


# Filas del Scenario Outline de RF-04
FILAS_RF04 = {
    "CHV-0000001": (
        ["CHV-0000001", "2026-05-06 10:09:31", GLOSA_CHV1, "Farmacia Aliada", "84617", "Unidad de Salud Valle Claro"],
        "CUBRE", "COV-005", 50, "42308.50", NOMBRE,
    ),
    "CHV-0000002": (
        ["CHV-0000002", "2026-05-04 10:45:37", "Paciente: Tomás Reyes Morales; DNO: DNO-21039776; SeguroSocial: SS-738-37-9115; Edad: 74; PerfilCobertura: PRIORITARIO; ServicioSolicitado: Suministro de antihipertensivos; Medicacion: hidroclorotiazida|losartán|amlodipino", "Portal Ciudadano", "53874", "Hospital Universitario del Este"],
        "CUBRE", "COV-013", 100, "53874.00", "Tomás Reyes Morales",
    ),
    "CHV-0000004": (
        ["CHV-0000004", "2026-05-05 12:11:20", "Paciente: Tomás Aguilar Ramírez; DNO: DNO-86274255; SeguroSocial: SS-444-18-6994; Edad: 30; PerfilCobertura: PRIORITARIO; ServicioSolicitado: Tratamiento spa terapéutico premium; Medicacion: magnesio|suplemento vitamínico|aceites esenciales", "Ventanilla Física", "903765", "Clínica Integral San Gregor"],
        "NO_CUBRE", "NO_CUBIERTO", 0, "0.00", "Tomás Aguilar Ramírez",
    ),
    "CHV-0000005": (
        ["CHV-0000005", "2026-05-06 11:11:57", "Paciente: Luis Aguilar Reyes; DNO: DNO-28919833; SeguroSocial: SS-345-84-5079; Edad: 56; PerfilCobertura: COPAGO; ServicioSolicitado: Medicina alternativa no certificada; Medicacion: suplemento herbal|ginkgo biloba", "Portal Ciudadano", "661684", "Hospital Central de Chernovia"],
        "NO_CUBRE", "NO_CUBIERTO", 0, "0.00", "Luis Aguilar Reyes",
    ),
    "CHV-0000006": (
        ["CHV-0000006", "2026-05-04 06:08:52", "Paciente: Elena Castro Delgado; DNO: DNO-48288801; SeguroSocial: SS-980-38-1666; Edad: 15; PerfilCobertura: PRIORITARIO; ServicioSolicitado: Hemograma completo; Medicacion: ninguna", "Farmacia Aliada", "49134", "Instituto Ambulatorio Novaterra"],
        "CUBRE", "COV-006", 100, "49134.00", "Elena Castro Delgado",
    ),
}


class BaseSAOM(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalogo = CatalogoCOIL(
            servicios_path=REF_DIR / "COIL_catalogo_servicios_cubiertos.csv",
            perfiles_path=REF_DIR / "COIL_catalogo_perfiles_cobertura.csv",
            version="COIL-2026.1",
        )

    def adjudicar(self, campos: List[str], **kwargs):
        dec, rech = adjudicar_fila_csv(campos, "LOTE-BDD", 0, 1, self.catalogo, CLAVE_SECRETA_TEST, **kwargs)
        self.assertIsNone(rech)
        self.assertIsNotNone(dec)
        return dec

    def procesar_csv(self, filas: Sequence[Sequence[str]]):
        buffer = io.StringIO()
        csv.writer(buffer, lineterminator="\n").writerows(filas)
        datos = buffer.getvalue().encode("utf-8")
        desc = DescriptorChunk("LOTE-BDD", 0, 0, len(datos) - 1, len(filas))
        return procesar_rango_bytes_csv(datos, desc, self.catalogo, CLAVE_SECRETA_TEST)


class TestRF01(BaseSAOM):
    def test_rf01_escenario_ingesta_estructura_integra(self) -> None:
        dec = self.adjudicar(fila_coil(GLOSA_CHV1))
        self.assertEqual(dec.estado, "VALIDATED")
        self.assertEqual(dec.id_solicitud, "CHV-0000001")
        self.assertEqual(dec.fecha_solicitud, "2026-05-06 10:09:31")
        self.assertEqual(dec.medio_emisor, "Farmacia Aliada")
        self.assertEqual(dec.entidad_emisora, "Unidad de Salud Valle Claro")
        self.assertEqual(dec.valor_procedimiento, Decimal("84617.00"))
        self.assertEqual(dec.perfil_cobertura, "ESTANDAR")
        self.assertEqual(len(dec.patient_token), 64)
        self.assertIn("#", dec.glosa_enmascarada)

    def test_rf01_escenario_fila_malformada_no_aborta_chunk(self) -> None:
        casos = {
            "sin_valor_procedimiento": fila_coil(GLOSA_CHV1, valor="", id_solicitud="CHV-9999999"),
            "glosa_vacia": fila_coil("", id_solicitud="CHV-9999999"),
        }
        for nombre, malformada in casos.items():
            with self.subTest(nombre):
                filas = [fila_coil(GLOSA_CHV1, id_solicitud=f"CHV-{i:07d}") for i in range(1, 4999)]
                filas.insert(2500, malformada)
                filas.append(fila_coil(GLOSA_CHV1, id_solicitud="CHV-0004999"))
                self.assertEqual(len(filas), 5000)
                res = self.procesar_csv(filas)
                self.assertEqual(res.ordenes_validas, 4999)
                self.assertEqual(res.ordenes_rechazadas, 1)
                self.assertEqual(res.rechazos[0].id_solicitud, "CHV-9999999")
                self.assertEqual(res.rechazos[0].estado, "REJECTED_SYNTAX")
                self.assertEqual(coincidencias_pii(salida_a_texto(res.rechazos[0]), [NOMBRE]), [])

    def test_rf01_rechazo_no_repite_texto_crudo_con_pii(self) -> None:
        casos = {
            "pii_en_valor": fila_coil(GLOSA_CHV1, valor=f"{NOMBRE} {DNO}"),
            "pii_en_primer_campo": [f"{NOMBRE} {DNO} {SS}", "x", "y"],
        }
        for nombre, campos in casos.items():
            with self.subTest(nombre):
                _, rechazo = adjudicar_fila_csv(campos, "LOTE-BDD", 0, 7, self.catalogo, CLAVE_SECRETA_TEST)
                self.assertEqual(rechazo.estado, "REJECTED_SYNTAX")
                self.assertEqual(coincidencias_pii(salida_a_texto(rechazo), [NOMBRE]), [])


class TestRF02(BaseSAOM):
    def test_rf02_escenario_extraccion_exitosa_con_spans(self) -> None:
        token, enmascarada, ent = extraer_y_pseudonimizar_glosa(GLOSA_CHV1, CLAVE_SECRETA_TEST)

        self.assertRegex(token, r"^[0-9a-f]{64}$")
        otro_dno = GLOSA_CHV1.replace(DNO, "DNO-23291912")
        otro_ss = GLOSA_CHV1.replace(SS, "SS-173-47-2764")
        self.assertNotEqual(extraer_y_pseudonimizar_glosa(otro_dno, CLAVE_SECRETA_TEST)[0], token)
        self.assertNotEqual(extraer_y_pseudonimizar_glosa(otro_ss, CLAVE_SECRETA_TEST)[0], token)
        self.assertNotEqual(extraer_y_pseudonimizar_glosa(GLOSA_CHV1, b"otra-clave")[0], token)
        self.assertEqual(extraer_y_pseudonimizar_glosa(GLOSA_CHV1, CLAVE_SECRETA_TEST)[0], token)

        self.assertEqual(len(GLOSA_CHV1), 235)
        self.assertEqual(len(enmascarada), 235)
        self.assertEqual(coincidencias_pii(enmascarada, [NOMBRE]), [])
        self.assertIn("#" * len(NOMBRE), enmascarada)
        self.assertIn("#" * len(DNO), enmascarada)
        self.assertIn("#" * len(SS), enmascarada)

        self.assertEqual(ent.edad, 14)
        self.assertEqual(ent.perfil_cobertura, "ESTANDAR")
        self.assertEqual(ent.servicio_solicitado, "Terapia física ambulatoria")
        esperado = {ent.edad_span: "14", ent.perfil_span: "ESTANDAR", ent.servicio_span: "Terapia física ambulatoria"}
        for (ini, fin), texto in esperado.items():
            self.assertEqual(GLOSA_CHV1[ini:fin], texto)
            self.assertEqual(enmascarada[ini:fin], texto)
        self.assertEqual(
            [m[0] for m in ent.medicaciones],
            ["acetaminofén", "diclofenaco tópico", "naproxeno", "ciclobenzaprina"],
        )
        for nombre, ini, fin in ent.medicaciones:
            self.assertEqual(GLOSA_CHV1[ini:fin], nombre)
            self.assertEqual(enmascarada[ini:fin], nombre)
        self.assertEqual(ent.confianza, 1.0)
        self.assertEqual(ent.flags, [])

    def test_rf02_escenario_incertidumbre_clinica(self) -> None:
        casos = {
            "sin_perfil": glosa_coil(omitir=["PerfilCobertura"]),
            "sin_edad": glosa_coil(omitir=["Edad"]),
            "sin_servicio": glosa_coil(omitir=["ServicioSolicitado"]),
            "sin_medicacion": glosa_coil(omitir=["Medicacion"]),
            "edad_no_numerica": glosa_coil(Edad="catorce"),
            "edad_fuera_de_rango": glosa_coil(Edad="200"),
            "servicio_vacio": glosa_coil(ServicioSolicitado=" "),
            "medicacion_vacia": glosa_coil(Medicacion="| |"),
        }
        for nombre, glosa in casos.items():
            with self.subTest(nombre):
                dec = self.adjudicar(fila_coil(glosa))
                self.assertEqual(dec.flags.count(UNCERTAINTY), 1)
                self.assertNotIn(PERFIL_DESCONOCIDO, dec.flags)
                self.assertEqual(dec.confianza, CASI_CUATRO)

    def test_p04_confianza_es_dato_y_no_activa_el_flag(self) -> None:
        casos = {"sin_paciente": glosa_coil(omitir=["Paciente"]), "dno_mal_formado": glosa_coil(DNO="DNO-12")}
        for nombre, glosa in casos.items():
            with self.subTest(nombre):
                dec = self.adjudicar(fila_coil(glosa))
                self.assertEqual(dec.confianza, CASI_CUATRO)
                self.assertEqual(dec.flags, [])


class TestRF03(BaseSAOM):
    def test_rf03_escenario_servicio_en_catalogo(self) -> None:
        glosa = glosa_coil(ServicioSolicitado="Control de hipertensión arterial", Medicacion="losartán|enalapril")
        dec = self.adjudicar(fila_coil(glosa, valor="124225"))
        self.assertEqual(dec.dictamen, "CUBRE")
        self.assertEqual(dec.codigo_servicio, "COV-009")
        self.assertEqual(dec.categoria_servicio, "Crónicos")
        self.assertIn("COV-009", dec.regla_ids)
        self.assertEqual(dec.flags, [])

    def test_rf03_escenario_valor_y_medicacion_fuera_de_referencia(self) -> None:
        glosa = glosa_coil(ServicioSolicitado="Control de hipertensión arterial", Medicacion="ibuprofeno")
        dec = self.adjudicar(fila_coil(glosa, valor="150000"))
        self.assertEqual(dec.dictamen, "CUBRE")
        self.assertEqual(sorted(dec.flags), sorted([FUERA_RANGO, MED_NO_REF]))

    def test_rf03_escenario_servicio_no_catalogado(self) -> None:
        glosa = glosa_coil(ServicioSolicitado="Tratamiento spa terapéutico premium", PerfilCobertura="PRIORITARIO")
        dec = self.adjudicar(fila_coil(glosa, valor="903765"))
        self.assertEqual(dec.dictamen, "NO_CUBRE")
        self.assertEqual(dec.causal_glosa, "GLOSA-EXCL-SERVICIO-NO-CUBIERTO")
        self.assertEqual(dec.porcentaje, 0)

    def test_p03_flags_independientes_y_limites_del_rango(self) -> None:
        hta = "Control de hipertensión arterial"
        casos = [
            ("limite_inferior", hta, "losartán", "50000", []),
            ("limite_superior", hta, "losartán", "130000", []),
            ("bajo_el_rango", hta, "losartán", "49999", [FUERA_RANGO]),
            ("solo_medicacion", hta, "losartán|ibuprofeno", "90000", [MED_NO_REF]),
            ("referencia_ninguna_sin_medicacion", "Hemograma completo", "ninguna", "49134", []),
            ("referencia_ninguna_con_medicacion", "Hemograma completo", "ibuprofeno", "49134", [MED_NO_REF]),
        ]
        for nombre, servicio, med, valor, flags in casos:
            with self.subTest(nombre):
                dec = self.adjudicar(fila_coil(glosa_coil(ServicioSolicitado=servicio, Medicacion=med), valor=valor))
                self.assertEqual(dec.dictamen, "CUBRE")
                self.assertEqual(dec.flags, flags)
                self.assertEqual(dec.porcentaje, 50)


class TestRF04(BaseSAOM):
    def verificar_fila(self, id_solicitud: str) -> None:
        campos, dictamen, codigo, porcentaje, aprobado, _ = FILAS_RF04[id_solicitud]
        dec = self.adjudicar(campos)
        self.assertEqual(dec.dictamen, dictamen)
        self.assertEqual(dec.codigo_servicio, codigo)
        self.assertEqual(dec.porcentaje, porcentaje)
        self.assertEqual(dec.valor_aprobado, Decimal(aprobado))
        self.assertEqual(dec.valor_copago, Decimal(campos[4]) - Decimal(aprobado))

    def test_rf04_outline_chv_0000001(self) -> None:
        self.verificar_fila("CHV-0000001")

    def test_rf04_outline_chv_0000002(self) -> None:
        self.verificar_fila("CHV-0000002")

    def test_rf04_outline_chv_0000004(self) -> None:
        self.verificar_fila("CHV-0000004")

    def test_rf04_outline_chv_0000005(self) -> None:
        self.verificar_fila("CHV-0000005")

    def test_rf04_outline_chv_0000006(self) -> None:
        self.verificar_fila("CHV-0000006")

    def test_p14_copago_es_siempre_la_diferencia(self) -> None:
        casos = {
            "prioritario": glosa_coil(PerfilCobertura="PRIORITARIO"),
            "estandar": glosa_coil(PerfilCobertura="ESTANDAR"),
            "copago": glosa_coil(PerfilCobertura="COPAGO"),
            "no_cubre": glosa_coil(ServicioSolicitado="Ortodoncia estética avanzada"),
            "perfil_fuera_de_catalogo": glosa_coil(PerfilCobertura="VIP"),
            "sin_perfil": glosa_coil(omitir=["PerfilCobertura"]),
        }
        for nombre, glosa in casos.items():
            with self.subTest(nombre):
                dec = self.adjudicar(fila_coil(glosa))
                self.assertEqual(dec.valor_copago, dec.valor_procedimiento - dec.valor_aprobado)

    def test_p17_perfil_fuera_del_catalogo(self) -> None:
        cubierto = self.adjudicar(fila_coil(glosa_coil(PerfilCobertura="VIP")))
        self.assertEqual(cubierto.dictamen, "CUBRE")
        self.assertEqual(cubierto.flags, [PERFIL_DESCONOCIDO])
        self.assertEqual(cubierto.porcentaje, 0)
        self.assertEqual(cubierto.valor_aprobado, Decimal("0.00"))
        self.assertEqual(cubierto.valor_copago, Decimal("84617.00"))
        self.assertEqual(cubierto.confianza, CASI_CUATRO)

        no_cubierto = self.adjudicar(
            fila_coil(glosa_coil(PerfilCobertura="VIP", ServicioSolicitado="Ortodoncia estética avanzada"))
        )
        self.assertEqual(no_cubierto.dictamen, "NO_CUBRE")
        self.assertEqual(no_cubierto.flags, [PERFIL_DESCONOCIDO])
        self.assertEqual(no_cubierto.porcentaje, 0)

    def test_perfil_ausente_lleva_solo_incertidumbre(self) -> None:
        dec = self.adjudicar(fila_coil(glosa_coil(omitir=["PerfilCobertura"])))
        self.assertEqual(dec.dictamen, "CUBRE")
        self.assertEqual(dec.flags, [UNCERTAINTY])
        self.assertEqual(dec.porcentaje, 0)

    def test_redondeo_round_half_up(self) -> None:
        dec = self.adjudicar(fila_coil(glosa_coil(PerfilCobertura="COPAGO"), valor="100000.02"))
        self.assertEqual(dec.valor_aprobado, Decimal("25000.01"))
        self.assertEqual(dec.valor_copago, Decimal("75000.01"))

    def test_t1_la_liquidacion_no_usa_float(self) -> None:
        dec = self.adjudicar(fila_coil(GLOSA_CHV1))
        for monto in (dec.valor_procedimiento, dec.valor_aprobado, dec.valor_copago):
            self.assertIsInstance(monto, Decimal)
        canonico = dec.to_canonical_dict()
        self.assertEqual(canonico["valor_aprobado"], "42308.50")
        self.assertEqual(canonico["valor_procedimiento"], "84617.00")

        arbol = ast.parse(Path(saom_core.__file__).read_text(encoding="utf-8"))
        funcion = next(n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef) and n.name == "adjudicar_fila_csv")
        for nodo in ast.walk(funcion):
            self.assertFalse(isinstance(nodo, ast.Name) and nodo.id == "float", "usa float()")
            self.assertFalse(isinstance(nodo, ast.Constant) and isinstance(nodo.value, float), "usa un literal float")


class TestRF05(BaseSAOM):
    def setUp(self) -> None:
        self.dec = self.adjudicar(fila_coil(GLOSA_CHV1), modelo_version="coil-parser-v1.0")

    def test_rf05_escenario_recibo_firmado_y_verificacion(self) -> None:
        dec = self.dec
        self.assertEqual(dec.dictamen, "CUBRE")
        self.assertIn("COV-005", dec.regla_ids)
        self.assertEqual(dec.catalogo_version, "COIL-2026.1")
        self.assertEqual(dec.modelo_version, "coil-parser-v1.0")
        self.assertRegex(dec.hash_decision, r"^[0-9a-f]{64}$")

        canonico = json.dumps(dec.to_canonical_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(hashlib.sha256(canonico.encode("utf-8")).hexdigest(), dec.hash_decision)
        self.assertNotIn(" ", canonico.replace("Terapia", ""))
        for campo in ("id_solicitud", "patient_token", "catalogo_version", "modelo_version", "regla_ids", "spans", "perfil_cobertura", "porcentaje", "valor_procedimiento", "valor_aprobado"):
            self.assertIn(campo, dec.to_canonical_dict())

        recibo_worm = dec.hash_decision
        raiz_chunk = calcular_raiz_chunk([dec])
        self.assertTrue(verificar_integridad_orden(dec, recibo_worm, [dec], raiz_chunk))

        dec.valor_aprobado += Decimal("0.01")
        self.assertFalse(verificar_integridad_orden(dec, recibo_worm, [dec], raiz_chunk))

    def test_t1_un_centavo_o_un_caracter_cambia_el_hash(self) -> None:
        base = self.dec.to_canonical_dict()
        cambios = {
            "valor_aprobado_centavo": {"valor_aprobado": "42308.51"},
            "valor_procedimiento_centavo": {"valor_procedimiento": "84617.01"},
            "id_solicitud": {"id_solicitud": "CHV-0000002"},
            "patient_token": {"patient_token": "0" + str(base["patient_token"])[1:]},
            "catalogo_version": {"catalogo_version": "COIL-2026.2"},
            "modelo_version": {"modelo_version": "coil-parser-v1.1"},
            "perfil_cobertura": {"perfil_cobertura": "ESTANDAS"},
            "dictamen": {"dictamen": "CUBRf"},
            "regla_ids": {"regla_ids": ["COV-006", "PERFIL-ESTANDAR-50"]},
            "porcentaje": {"porcentaje": 51},
            "spans": {"spans": {**base["spans"], "Edad": [0, 1]}},
        }
        original = calcular_hash_decision(base)
        self.assertEqual(original, self.dec.hash_decision)
        for nombre, cambio in cambios.items():
            with self.subTest(nombre):
                self.assertNotEqual(calcular_hash_decision({**base, **cambio}), original)

    def test_rf05_decision_repetida_produce_el_mismo_hash(self) -> None:
        self.assertEqual(self.adjudicar(fila_coil(GLOSA_CHV1), modelo_version="coil-parser-v1.0").hash_decision, self.dec.hash_decision)

    def test_rf05_raices_son_concatenacion_ordenada_sha256(self) -> None:
        otra = self.adjudicar(fila_coil(GLOSA_CHV1, id_solicitud="CHV-0000002"))
        esperada = hashlib.sha256((self.dec.hash_decision + otra.hash_decision).encode("utf-8")).hexdigest()
        self.assertEqual(calcular_raiz_chunk([otra, self.dec]), esperada)
        self.assertEqual(calcular_raiz_chunk([self.dec, otra]), esperada)
        lote = hashlib.sha256(("a" * 64 + "b" * 64).encode("utf-8")).hexdigest()
        self.assertEqual(calcular_raiz_lote([(1, "b" * 64), (0, "a" * 64)]), lote)


class TestCriteriosT1(BaseSAOM):
    def test_t1_spans_iguales_en_glosa_original_y_enmascarada(self) -> None:
        for id_solicitud, (campos, *_) in FILAS_RF04.items():
            with self.subTest(id_solicitud):
                dec = self.adjudicar(campos)
                glosa = campos[2]
                self.assertEqual(len(glosa), len(dec.glosa_enmascarada))
                for clave, (ini, fin) in dec.spans.items():
                    self.assertEqual(glosa[ini:fin], dec.glosa_enmascarada[ini:fin], clave)
                    self.assertNotIn("#", glosa[ini:fin])
                for med in dec.medicaciones:
                    ini, fin = med["span_inicio"], med["span_fin"]
                    self.assertEqual(glosa[ini:fin], med["nombre"])
                    self.assertEqual(dec.glosa_enmascarada[ini:fin], med["nombre"])

    def test_t1_cero_pii_en_las_salidas(self) -> None:
        filas = [datos[0] for datos in FILAS_RF04.values()]
        filas.append(fila_coil(GLOSA_CHV1, valor="", id_solicitud="CHV-9999999"))
        filas.append(fila_coil(glosa_coil(PerfilCobertura="VIP"), id_solicitud="CHV-0000007"))
        filas.append(fila_coil(glosa_coil(omitir=["Edad"]), id_solicitud="CHV-0000008"))
        nombres = [datos[5] for datos in FILAS_RF04.values()]

        res = self.procesar_csv(filas)
        self.assertEqual(res.ordenes_validas + res.ordenes_rechazadas, len(filas))
        self.assertEqual(res.ordenes_rechazadas, 1)
        texto = " ".join(salida_a_texto(s) for s in [*res.decisiones, *res.rechazos])
        self.assertEqual(coincidencias_pii(texto, nombres), [])

    def test_t1_el_escaneo_de_pii_detecta_datos_en_claro(self) -> None:
        self.assertEqual(coincidencias_pii(GLOSA_CHV1, [NOMBRE]), [DNO, SS, NOMBRE])


if __name__ == "__main__":
    unittest.main(verbosity=2)
