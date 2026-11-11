"""Pruebas automatizadas para la muestra T5a (600 glosas) y la evaluación F1 + M/M/c T5."""
from __future__ import annotations

import json
import re
from pathlib import Path

from evaluacion_f1_t5 import (
    ANOTADORES_EQUIPO,
    ENTIDADES_RNF02,
    construir_muestra_t5a,
    evaluar_f1_sobre_muestra,
    recalcular_mmc_y_costo_12m,
)


def test_t5a_muestra_600_estructura_anotadores_y_cero_pii(tmp_path: Path) -> None:
    """Verifica 300 limpias + 300 perturbadas, reparto 200x3 y ausencia total de PII (P-05, P-15)."""
    registros, ciega_path, ref_path = construir_muestra_t5a(output_dir=tmp_path)

    assert len(registros) == 600
    limpias = [r for r in registros if r.subconjunto == "LIMPIA"]
    perturbadas = [r for r in registros if r.subconjunto == "PERTURBADA"]
    assert len(limpias) == 300
    assert len(perturbadas) == 300

    # Verificar reparto equitativo entre Naomi Chow, Daniel Lopez y María Fernanda Toro
    for integrante in ANOTADORES_EQUIPO:
        asignadas = [r for r in registros if r.anotador_asignado == integrante]
        assert len(asignadas) == 200

    # Verificar que los archivos JSONL existen y tienen 600 líneas
    lineas_ciegas = ciega_path.read_text(encoding="utf-8").strip().splitlines()
    lineas_ref = ref_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lineas_ciegas) == 600
    assert len(lineas_ref) == 600

    # Verificar cero PII en claro en ambos archivos (ningún DNO ni NSS de dígitos ni nombres)
    patron_dno_claro = re.compile(r"DNO\s*:\s*\d{6,10}")
    patron_nss_claro = re.compile(r"SeguroSocial\s*:\s*\d{8,15}")
    for linea in lineas_ciegas + lineas_ref:
        obj = json.loads(linea)
        glosa = obj["glosa_enmascarada"]
        assert not patron_dno_claro.search(glosa)
        assert not patron_nss_claro.search(glosa)
        assert "#" in glosa

    # Verificar que todo span de referencia coincide exactamente con glosa[inicio:fin]
    for r in registros:
        for ent in r.etiquetas_referencia:
            assert r.glosa_evaluada[ent.start_char : ent.end_char] == ent.valor


def test_t5_f1_cumple_rnf02_y_fraccion_f_cumple_rnf03(tmp_path: Path) -> None:
    """Verifica F1 = 1.0000 en limpias, F1 >= 0.92 en perturbadas y global, y f <= 0.30."""
    registros, _, _ = construir_muestra_t5a(output_dir=tmp_path)

    res_limpias = evaluar_f1_sobre_muestra(registros, filtro_subconjunto="LIMPIA")
    res_pert = evaluar_f1_sobre_muestra(registros, filtro_subconjunto="PERTURBADA")
    res_global = evaluar_f1_sobre_muestra(registros, filtro_subconjunto=None)

    assert res_limpias["macro_f1"] == 1.0
    assert res_pert["macro_f1"] >= 0.92
    assert res_global["macro_f1"] >= 0.92
    assert res_global["cumple_rnf02_f1_092"] is True
    assert res_global["fraccion_revision_f"] <= 0.30

    for ent in ENTIDADES_RNF02:
        assert res_global["por_entidad"][ent]["f1"] >= 0.92


def test_t5_modelo_mmc_y_costo_por_millon() -> None:
    """Verifica que el recálculo M/M/c y de costos cumple RNF-01 y RNF-03."""
    res_p07 = recalcular_mmc_y_costo_12m(400.0)
    assert res_p07["mmc"]["3h"]["N_workers"] == 4
    assert res_p07["mmc"]["3h"]["rho"] < 1.0
    assert res_p07["costos"]["cumple_meta_rnf03_050_usd_m"] is True
