"""Independent conformance suite covering SPEC-013 (Satélite Sentinel-2 10 m).

Written by the tester role (Antigravity), not the implementer.
Tests map to requirements of SPEC-013 and verification scenarios in KIT-ACEITE-013.
"""

import ast
import json
import os
import uuid
from dataclasses import fields, is_dataclass
from datetime import date, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

import psycopg
import pytest

from seugado.sensing.earth_engine import (
    ObservacaoSatelite,
    amostrar_sentinel2,
    extrair_observacoes,
    inicializar_earth_engine,
)
from seugado.sensing.ingestao import ingerir_leituras

ROOT = Path(__file__).resolve().parents[2]
EARTH_ENGINE_PY = ROOT / "src" / "seugado" / "sensing" / "earth_engine.py"
INGESTAO_PY = ROOT / "src" / "seugado" / "sensing" / "ingestao.py"


# ==============================================================================
# Structural Checks (KIT-ACEITE-013)
# ==============================================================================


def test_files_under_300_lines() -> None:
    """earth_engine.py and ingestao.py must stay under 300 lines each."""
    ee_lines = EARTH_ENGINE_PY.read_text(encoding="utf-8").splitlines()
    assert len(ee_lines) <= 300, f"earth_engine.py exceeds 300 lines: {len(ee_lines)}"

    ing_lines = INGESTAO_PY.read_text(encoding="utf-8").splitlines()
    assert len(ing_lines) <= 300, f"ingestao.py exceeds 300 lines: {len(ing_lines)}"


def test_exact_collections_and_no_hls_reference() -> None:
    """Collections must be S2_SR_HARMONIZED and CLOUD_SCORE_PLUS; no HLS references."""
    ee_content = EARTH_ENGINE_PY.read_text(encoding="utf-8")
    ing_content = INGESTAO_PY.read_text(encoding="utf-8")

    assert "COPERNICUS/S2_SR_HARMONIZED" in ee_content
    assert "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED" in ee_content

    assert "HLS" not in ee_content
    assert "HLSS30" not in ee_content
    assert "HLS" not in ing_content


def test_sampling_parameters_buffer_scale_cs_cdf() -> None:
    """Verify negative buffer -5 m, scale 10 m, and cs_cdf >= 0.60 in earth_engine.py."""
    ee_content = EARTH_ENGINE_PY.read_text(encoding="utf-8")
    assert "buffer(-5)" in ee_content or "buffer(_BUFFER_M)" in ee_content
    assert "scale=10" in ee_content or "scale=_ESCALA_M" in ee_content
    assert "0.60" in ee_content or "0.6" in ee_content


def test_extrair_observacoes_is_pure_and_ingestao_does_not_commit() -> None:
    """extrair_observacoes is pure; ingerir_leituras does not commit or rebuild projection."""
    for file_path in (EARTH_ENGINE_PY, INGESTAO_PY):
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in ("commit", "reconstruir_projecao"), (
                    f"{file_path.name} forbidden call {node.func.attr}() on line {node.lineno}"
                )


def test_observacao_satelite_frozen_slotted_eight_fields() -> None:
    """ObservacaoSatelite is frozen, slotted, with exact 8 fields in order."""
    assert is_dataclass(ObservacaoSatelite)
    params = getattr(ObservacaoSatelite, "__dataclass_params__", None)
    assert params is not None and params.frozen is True
    assert hasattr(ObservacaoSatelite, "__slots__")

    expected_fields = [
        "piquete_id",
        "data",
        "ndvi",
        "refletancia_red",
        "refletancia_nir",
        "pixels_validos",
        "pixels_totais",
        "pct_nuvem",
    ]
    actual_fields = [f.name for f in fields(ObservacaoSatelite)]
    assert actual_fields == expected_fields


def test_idempotency_key_and_entidade_uuid5_format() -> None:
    """Key is leitura:<piquete_id>:<YYYY-MM-DD> and entidade_id is uuid5(NAMESPACE_URL, key)."""
    p_id = uuid.uuid4()
    d = date(2026, 9, 20)
    expected_key = f"leitura:{p_id}:{d.isoformat()}"
    assert uuid5(NAMESPACE_URL, expected_key) is not None

    ing_content = INGESTAO_PY.read_text(encoding="utf-8")
    assert 'f"leitura:{obs.piquete_id}:{obs.data.isoformat()}"' in ing_content
    assert "uuid5(NAMESPACE_URL, chave)" in ing_content


# ==============================================================================
# Canonical Case (KIT-ACEITE-013)
# ==============================================================================


def test_canonical_worked_example() -> None:
    """Exemplo resolvido da spec (P1, NDVI 0.75, 20% nuvem, refletâncias escaladas)."""
    p1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    p2 = uuid.UUID("22222222-2222-2222-2222-222222222222")

    rows = [
        {
            "piquete_id": str(p1),
            "data": "2026-09-20",
            "red": 500,
            "nir": 3500,
            "pixels_validos": 40,
            "pixels_totais": 50,
        },
        {
            "piquete_id": str(p1),
            "data": "2026-09-20",
            "red": 600,
            "nir": 3000,
            "pixels_validos": 12,
            "pixels_totais": 50,
        },
        {
            "piquete_id": str(p2),
            "data": "2026-09-20",
            "red": 500,
            "nir": 3000,
            "pixels_validos": 2,
            "pixels_totais": 50,
        },
    ]

    obs = extrair_observacoes(rows)
    assert len(obs) == 1, "P2 should be dropped (<3 pixels) and duplicate P1 deduplicated"

    o1 = obs[0]
    assert o1.piquete_id == p1
    assert o1.data == date(2026, 9, 20)
    assert o1.refletancia_red == pytest.approx(0.05, abs=0.0001)
    assert o1.refletancia_nir == pytest.approx(0.35, abs=0.0001)
    assert o1.ndvi == pytest.approx(0.75, abs=0.0001)
    assert o1.pct_nuvem == pytest.approx(20.0, abs=0.1)
    assert o1.pixels_validos == 40
    assert o1.pixels_totais == 50


# ==============================================================================
# Casos que a spec não mostra (KIT-ACEITE-013)
# ==============================================================================


def test_hidden_case_1_unscaled_reflectance_preserves_values() -> None:
    """Caso 1: Linha já em reflectância (red=0.05, nir=0.30) -> sem escala -> NDVI 0.7143."""
    p_id = uuid.uuid4()
    row = {
        "piquete_id": str(p_id),
        "data": "2026-09-25",
        "red": 0.05,
        "nir": 0.30,
        "pixels_validos": 20,
        "pixels_totais": 25,
    }
    obs = extrair_observacoes([row])
    assert len(obs) == 1
    o = obs[0]
    assert o.refletancia_red == pytest.approx(0.05)
    assert o.refletancia_nir == pytest.approx(0.30)
    # ndvi = (0.30 - 0.05) / (0.30 + 0.05) = 0.25 / 0.35 = 0.7142857...
    assert o.ndvi == pytest.approx(0.7143, abs=0.0001)
    assert o.pct_nuvem == pytest.approx(20.0, abs=0.1)


def test_hidden_case_2_tie_keeps_first_row() -> None:
    """Caso 2: Duas linhas do mesmo piquete/data com 20 pixels cada -> fica a primeira."""
    p_id = uuid.uuid4()
    rows = [
        {
            "piquete_id": str(p_id),
            "data": "2026-09-22",
            "red": 500,
            "nir": 3500,
            "pixels_validos": 20,
            "pixels_totais": 30,
        },
        {
            "piquete_id": str(p_id),
            "data": "2026-09-22",
            "red": 700,
            "nir": 2800,
            "pixels_validos": 20,
            "pixels_totais": 30,
        },
    ]
    obs = extrair_observacoes(rows)
    assert len(obs) == 1
    # First row has red 500 -> 0.05, nir 3500 -> 0.35
    assert obs[0].refletancia_red == pytest.approx(0.05)
    assert obs[0].refletancia_nir == pytest.approx(0.35)


def test_hidden_case_3_real_supabase_and_gee_ingestion() -> None:
    """Caso 3: Real (Supabase + GEE): piquetes ~0.1 e ~0.4 ha têm >= 1 leitura; 2a dá 0."""
    db_url = os.environ.get("SEUGADO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    gee_json = os.environ.get("SEUGADO_GEE_SERVICE_ACCOUNT_JSON")
    gee_proj = os.environ.get("SEUGADO_GEE_PROJECT")

    if not db_url or not gee_json or not gee_proj:
        pytest.skip("Credentials for live database or GEE not available; skipping live test")

    fazenda_id = uuid.uuid4()
    p1_id = uuid.uuid4()
    p2_id = uuid.uuid4()

    # ~0.1 ha polygon in São Miguel dos Campos, AL
    poly_01ha = {
        "type": "Polygon",
        "coordinates": [[
            [-36.0900, -9.7800],
            [-36.0897, -9.7800],
            [-36.0897, -9.7803],
            [-36.0900, -9.7803],
            [-36.0900, -9.7800],
        ]],
    }
    # ~0.4 ha polygon in São Miguel dos Campos, AL
    poly_04ha = {
        "type": "Polygon",
        "coordinates": [[
            [-36.0910, -9.7800],
            [-36.0904, -9.7800],
            [-36.0904, -9.7806],
            [-36.0910, -9.7806],
            [-36.0910, -9.7800],
        ]],
    }

    hoje = date(2026, 9, 27)
    inicio = hoje - timedelta(days=30)

    with psycopg.connect(db_url) as conn:
        try:
            with conn.cursor() as cur:
                # 1. Insert test farm
                cur.execute(
                    "INSERT INTO fazenda (id, nome, timezone, funcionarios_disponiveis,"
                    " animais_por_funcionario_dia) VALUES (%s, 'Fazenda Teste GEE',"
                    " 'America/Maceio', 1, 100)",
                    (fazenda_id,),
                )
                # 2. Insert test paddocks in estado_piquete
                cur.execute("SELECT id FROM cultivar LIMIT 1")
                row_c = cur.fetchone()
                cultivar_id = row_c[0] if row_c else uuid.uuid4()

                insert_p = (
                    "INSERT INTO estado_piquete (piquete_id, fazenda_id, cultivar_id,"
                    " nome, area_ha, metodo_pastejo, ativo, geometria, situacao,"
                    " desde, dias_descanso, derivado_ate_sequencia)"
                    " VALUES (%s, %s, %s, %s, %s, %s, true,"
                    " ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 'descansando', %s, %s, %s)"
                )
                cur.execute(
                    insert_p,
                    (
                        p1_id,
                        fazenda_id,
                        cultivar_id,
                        "P01",
                        0.1,
                        "rotacionado",
                        json.dumps(poly_01ha),
                        inicio,
                        0,
                        0,
                    ),
                )
                cur.execute(
                    insert_p,
                    (
                        p2_id,
                        fazenda_id,
                        cultivar_id,
                        "P04",
                        0.4,
                        "rotacionado",
                        json.dumps(poly_04ha),
                        inicio,
                        0,
                        0,
                    ),
                )

            # 3. Primeira execução: deve encontrar leituras e registrar novos eventos
            novas_primeira = ingerir_leituras(conn, fazenda_id, inicio, hoje)
            assert novas_primeira >= 2, f"Expected >= 2 readings, got {novas_primeira}"

            # Verify that both paddocks received readings
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload->>'piquete_id' FROM evento WHERE fazenda_id = %s",
                    (fazenda_id,),
                )
                p_ids_gravados = {UUID(r[0]) for r in cur.fetchall()}
                assert p1_id in p_ids_gravados, "Paddock 0.1 ha received no satellite readings"
                assert p2_id in p_ids_gravados, "Paddock 0.4 ha received no satellite readings"

            # 4. Segunda execução: idempotência -> devolve 0
            novas_segunda = ingerir_leituras(conn, fazenda_id, inicio, hoje)
            assert novas_segunda == 0, f"Expected 0 on second run, got {novas_segunda}"

        finally:
            conn.rollback()


# ==============================================================================
# Validation Checks (SPEC-013)
# ==============================================================================


def test_amostrar_sentinel2_inverted_dates_raises_value_error() -> None:
    """amostrar_sentinel2 with data_inicio > data_fim raises ValueError."""
    p_id = uuid.uuid4()
    poly = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
    }
    with pytest.raises(ValueError, match="data_inicio"):
        amostrar_sentinel2([(p_id, poly)], date(2026, 9, 20), date(2026, 9, 10))


def test_amostrar_sentinel2_invalid_geometry_raises_value_error() -> None:
    """Geometry that is not a Polygon raises ValueError before touching GEE."""
    p_id = uuid.uuid4()
    bad_geom = {"type": "Point", "coordinates": [0, 0]}
    with pytest.raises(ValueError, match="not a GeoJSON Polygon"):
        amostrar_sentinel2([(p_id, bad_geom)], date(2026, 9, 10), date(2026, 9, 20))


def test_inicializar_earth_engine_missing_env_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing SEUGADO_GEE_PROJECT or JSON raises RuntimeError naming it."""
    monkeypatch.setenv("SEUGADO_GEE_SERVICE_ACCOUNT_JSON", '{"client_email": "x"}')
    monkeypatch.delenv("SEUGADO_GEE_PROJECT", raising=False)
    with pytest.raises(RuntimeError, match="SEUGADO_GEE_PROJECT"):
        inicializar_earth_engine()

    monkeypatch.delenv("SEUGADO_GEE_SERVICE_ACCOUNT_JSON", raising=False)
    with pytest.raises(RuntimeError, match="SEUGADO_GEE_SERVICE_ACCOUNT_JSON"):
        inicializar_earth_engine()
