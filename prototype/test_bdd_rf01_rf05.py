"""Suite de Pruebas BDD automatizadas para RF-01 a RF-05 y RNF-02 a RNF-05 (Proyecto COIL)."""
from __future__ import annotations

import re
import unittest
from decimal import Decimal
from pathlib import Path

from saom_core import (
    CatalogoCOIL,
    DescriptorChunk,
    adjudicar_fila_csv,
    calcular_raiz_chunk,
    calcular_raiz_lote,
    extraer_y_pseudonimizar_glosa,
    procesar_rango_bytes_csv,
    verificar_integridad_orden,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REF_DIR = REPO_ROOT / "data" / "ref"
CLAVE_SECRETA_TEST = b"coil-chernovia-secret-hmac-key-2026"


class TestBDDSAOMChernovia(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalogo = CatalogoCOIL(
            servicios_path=REF_DIR / "COIL_catalogo_servicios_cubiertos.csv",
            perfiles_path=REF_DIR / "COIL_catalogo_perfiles_cobertura.csv",
            version="COIL-2026.1",
        )

    def test_rf01_validacion_y_aislamiento_rechazo_sintactico(self) -> None:
        """RF-01: Aísla una fila malformada como REJECTED_SYNTAX sin abortar el resto del chunk."""
        csv_chunk = (
            "CHV-0000001,2026-05-06 10:09:31,Paciente: Paula Vargas Ramírez; DNO: DNO-23291911; "
            "SeguroSocial: SS-173-47-2763; Edad: 14; PerfilCobertura: ESTANDAR; "
            "ServicioSolicitado: Terapia física ambulatoria; "
            "Medicacion: acetaminofén|diclofenaco tópico|naproxeno|ciclobenzaprina,"
            "Farmacia Aliada,84617,Unidad de Salud Valle Claro\n"
            "CHV-0000002-MAL,2026-05-06 10:10:00,,Farmacia Aliada,-500,Hospital X\n"
            "CHV-0000002,2026-05-04 10:45:37,Paciente: Tomás Reyes Morales; DNO: DNO-21039776; "
            "SeguroSocial: SS-738-37-9115; Edad: 74; PerfilCobertura: PRIORITARIO; "
            "ServicioSolicitado: Suministro de antihipertensivos; "
            "Medicacion: hidroclorotiazida|losartán|amlodipino,"
            "Portal Ciudadano,53874,Hospital Universitario del Este\n"
        ).encode("utf-8")

        desc = DescriptorChunk("LOTE-TEST-01", 0, 0, len(csv_chunk) - 1, 3)
        res = procesar_rango_bytes_csv(csv_chunk, desc, self.catalogo, CLAVE_SECRETA_TEST)

        self.assertEqual(res.ordenes_validas, 2)
        self.assertEqual(res.ordenes_rechazadas, 1)
        self.assertEqual(res.rechazos[0].id_solicitud, "CHV-0000002-MAL")
        self.assertEqual(res.rechazos[0].estado, "REJECTED_SYNTAX")

    def test_rf02_rnf05_pseudonimizacion_longitud_fija_y_spans_exactos(self) -> None:
        """RF-02 y RNF-05: Enmascara PII con '#' preservando la longitud y los spans exactos."""
        glosa = (
            "Paciente: Paula Vargas Ramírez; DNO: DNO-23291911; SeguroSocial: SS-173-47-2763; "
            "Edad: 14; PerfilCobertura: ESTANDAR; ServicioSolicitado: Terapia física ambulatoria; "
            "Medicacion: acetaminofén|diclofenaco tópico|naproxeno|ciclobenzaprina"
        )
        token, enmascarada, ent = extraer_y_pseudonimizar_glosa(glosa, CLAVE_SECRETA_TEST)

        # 1. Longitud idéntica
        self.assertEqual(len(enmascarada), len(glosa))
        # 2. Cero PII en claro en la glosa enmascarada
        self.assertNotIn("Paula Vargas Ramírez", enmascarada)
        self.assertNotIn("DNO-23291911", enmascarada)
        self.assertNotIn("SS-173-47-2763", enmascarada)
        self.assertIsNone(re.search(r"DNO-\d+", enmascarada))
        self.assertIsNone(re.search(r"SS-\d{3}-\d{2}-\d{4}", enmascarada))
        # 3. Los spans apuntan exactamente a los mismos caracteres en la glosa original y en la enmascarada
        assert ent.edad_span is not None
        assert ent.perfil_span is not None
        assert ent.servicio_span is not None
        self.assertEqual(glosa[ent.edad_span[0] : ent.edad_span[1]], "14")
        self.assertEqual(enmascarada[ent.edad_span[0] : ent.edad_span[1]], "14")
        self.assertEqual(glosa[ent.perfil_span[0] : ent.perfil_span[1]], "ESTANDAR")
        self.assertEqual(
            glosa[ent.servicio_span[0] : ent.servicio_span[1]],
            "Terapia física ambulatoria",
        )
        self.assertEqual(
            enmascarada[ent.servicio_span[0] : ent.servicio_span[1]],
            "Terapia física ambulatoria",
        )
        # 4. Spans individuales de cada medicación
        meds_nombres = [m[0] for m in ent.medicaciones]
        self.assertEqual(
            meds_nombres,
            ["acetaminofén", "diclofenaco tópico", "naproxeno", "ciclobenzaprina"],
        )
        for nombre, ini, fin in ent.medicaciones:
            self.assertEqual(glosa[ini:fin], nombre)
            self.assertEqual(enmascarada[ini:fin], nombre)
        # 5. Confianza >= 0.92
        self.assertGreaterEqual(ent.confianza, 0.92)

    def test_rf03_rf04_tabla_ejemplos_bdd_liquidacion(self) -> None:
        """RF-03 y RF-04: Verifica el Scenario Outline con CHV-0000001 a CHV-0000006 del dataset real."""
        casos = [
            (
                [
                    "CHV-0000001",
                    "2026-05-06 10:09:31",
                    "Paciente: Paula Vargas Ramírez; DNO: DNO-23291911; SeguroSocial: SS-173-47-2763; Edad: 14; PerfilCobertura: ESTANDAR; ServicioSolicitado: Terapia física ambulatoria; Medicacion: acetaminofén|diclofenaco tópico|naproxeno|ciclobenzaprina",
                    "Farmacia Aliada",
                    "84617",
                    "Unidad de Salud Valle Claro",
                ],
                "CUBRE",
                "COV-005",
                50,
                Decimal("42308.50"),
            ),
            (
                [
                    "CHV-0000002",
                    "2026-05-04 10:45:37",
                    "Paciente: Tomás Reyes Morales; DNO: DNO-21039776; SeguroSocial: SS-738-37-9115; Edad: 74; PerfilCobertura: PRIORITARIO; ServicioSolicitado: Suministro de antihipertensivos; Medicacion: hidroclorotiazida|losartán|amlodipino",
                    "Portal Ciudadano",
                    "53874",
                    "Hospital Universitario del Este",
                ],
                "CUBRE",
                "COV-013",
                100,
                Decimal("53874.00"),
            ),
            (
                [
                    "CHV-0000004",
                    "2026-05-05 12:11:20",
                    "Paciente: Tomás Aguilar Ramírez; DNO: DNO-86274255; SeguroSocial: SS-444-18-6994; Edad: 30; PerfilCobertura: PRIORITARIO; ServicioSolicitado: Tratamiento spa terapéutico premium; Medicacion: magnesio|suplemento vitamínico|aceites esenciales",
                    "Ventanilla Física",
                    "903765",
                    "Clínica Integral San Gregor",
                ],
                "NO_CUBRE",
                "NO_CUBIERTO",
                0,
                Decimal("0.00"),
            ),
            (
                [
                    "CHV-0000005",
                    "2026-05-06 11:11:57",
                    "Paciente: Luis Aguilar Reyes; DNO: DNO-28919833; SeguroSocial: SS-345-84-5079; Edad: 56; PerfilCobertura: COPAGO; ServicioSolicitado: Medicina alternativa no certificada; Medicacion: suplemento herbal|ginkgo biloba",
                    "Portal Ciudadano",
                    "661684",
                    "Hospital Central de Chernovia",
                ],
                "NO_CUBRE",
                "NO_CUBIERTO",
                0,
                Decimal("0.00"),
            ),
            (
                [
                    "CHV-0000006",
                    "2026-05-04 06:08:52",
                    "Paciente: Elena Castro Delgado; DNO: DNO-48288801; SeguroSocial: SS-980-38-1666; Edad: 15; PerfilCobertura: PRIORITARIO; ServicioSolicitado: Hemograma completo; Medicacion: ninguna",
                    "Farmacia Aliada",
                    "49134",
                    "Instituto Ambulatorio Novaterra",
                ],
                "CUBRE",
                "COV-006",
                100,
                Decimal("49134.00"),
            ),
        ]

        for campos, esp_dictamen, esp_cod, esp_pct, esp_aprobado in casos:
            dec, rech = adjudicar_fila_csv(
                campos, "LOTE-BDD", 0, 1, self.catalogo, CLAVE_SECRETA_TEST
            )
            self.assertIsNone(rech)
            assert dec is not None
            self.assertEqual(dec.dictamen, esp_dictamen)
            self.assertEqual(dec.codigo_servicio, esp_cod)
            self.assertEqual(dec.porcentaje, esp_pct)
            self.assertEqual(dec.valor_aprobado, esp_aprobado)

    def test_rf05_rnf04_trazabilidad_inmutable_y_deteccion_alteracion(self) -> None:
        """RF-05 y RNF-04: Verifica árbol de hashes y detección ante alteración de 1 centavo."""
        fila = [
            "CHV-0000001",
            "2026-05-06 10:09:31",
            "Paciente: Paula Vargas Ramírez; DNO: DNO-23291911; SeguroSocial: SS-173-47-2763; Edad: 14; PerfilCobertura: ESTANDAR; ServicioSolicitado: Terapia física ambulatoria; Medicacion: acetaminofén|diclofenaco tópico|naproxeno|ciclobenzaprina",
            "Farmacia Aliada",
            "84617",
            "Unidad de Salud Valle Claro",
        ]
        dec, _ = adjudicar_fila_csv(fila, "LOTE-HASH", 0, 1, self.catalogo, CLAVE_SECRETA_TEST)
        assert dec is not None
        recibo_worm = dec.hash_decision
        raiz_chunk = calcular_raiz_chunk([dec])
        raiz_lote = calcular_raiz_lote([(0, raiz_chunk)])
        self.assertEqual(len(raiz_lote), 64)

        # Verificación íntegra exitosa
        self.assertTrue(verificar_integridad_orden(dec, recibo_worm, [dec], raiz_chunk))

        # Si alguien altera valor_aprobado por 1 centavo en la tabla analítica, la verificación falla
        dec.valor_aprobado += Decimal("0.01")
        self.assertFalse(verificar_integridad_orden(dec, recibo_worm, [dec], raiz_chunk))


if __name__ == "__main__":
    unittest.main(verbosity=2)
