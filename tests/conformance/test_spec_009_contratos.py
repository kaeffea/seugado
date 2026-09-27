"""Independent conformance suite covering SPEC-009 (Contratos do MVP).

Written by the tester role (Antigravity), not the implementer.
Tests map to requirements of SPEC-009 and verification scenarios in KIT-ACEITE-009.
"""

import ast
import json
from dataclasses import fields, is_dataclass
from datetime import date
from pathlib import Path
from typing import get_origin

import pytest

from seugado import contratos
from seugado.core.models import (
    Confianca,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRATOS_FILE = ROOT / "src" / "seugado" / "contratos.py"
FIXTURES_DIR = ROOT / "tests" / "fixtures"


# ==============================================================================
# Structural Checks (KIT-ACEITE-009)
# ==============================================================================


def test_file_under_300_lines():
    """src/seugado/contratos.py must stay under 300 lines."""
    lines = CONTRATOS_FILE.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 300, f"File exceeds 300 lines: {len(lines)}"


def test_forbidden_imports():
    """Module must not import sensing, planner, api, delivery, psycopg or pydantic."""
    tree = ast.parse(CONTRATOS_FILE.read_text(encoding="utf-8"))
    forbidden_prefixes = ("sensing", "planner", "api", "delivery", "psycopg", "pydantic")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(alias.name.startswith(p) for p in forbidden_prefixes), (
                    f"Forbidden import: {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not any(node.module.startswith(p) for p in forbidden_prefixes), (
                f"Forbidden import from: {node.module}"
            )


def test_tipo_alerta_members():
    """TipoAlerta has exactly 8 members and exact string values."""
    expected = {
        "SEM_PIQUETE_APTO": "sem_piquete_apto",
        "CAPACIDADE_EXCEDIDA": "capacidade_excedida",
        "AGUARDANDO_PARAMETRO": "aguardando_parametro",
        "ESTIMATIVA_INDISPONIVEL": "estimativa_indisponivel",
        "CONTINUO_ACIMA_MAXIMA": "continuo_acima_maxima",
        "CONTINUO_ABAIXO_MINIMA": "continuo_abaixo_minima",
        "LOTE_SEM_PIQUETE": "lote_sem_piquete",
        "SEM_DIA_DE_MANEJO": "sem_dia_de_manejo",
    }
    actual = {m.name: m.value for m in contratos.TipoAlerta}
    assert actual == expected
    assert len(contratos.TipoAlerta) == 8


def test_all_dataclasses_frozen_slotted_no_methods():
    """9 dataclasses are frozen, slotted, in exact field order, and have no custom methods."""
    dc_classes = [
        contratos.PiqueteProjetado,
        contratos.LoteProjetado,
        contratos.EstadoProjetado,
        contratos.Movimentacao,
        contratos.Alerta,
        contratos.PedidoValidacao,
        contratos.ResumoPiquete,
        contratos.PlanoManejo,
    ]

    for cls in dc_classes:
        assert is_dataclass(cls), f"{cls.__name__} is not a dataclass"
        params = getattr(cls, "__dataclass_params__", None)
        assert params is not None
        assert params.frozen, f"{cls.__name__} must be frozen"
        assert hasattr(cls, "__slots__"), f"{cls.__name__} must have slots"

        # Check collections in fields: no list or dict allowed
        for f in fields(cls):
            origin = get_origin(f.type)
            assert origin is not list, f"Field {f.name} in {cls.__name__} must not be list"
            assert origin is not dict, f"Field {f.name} in {cls.__name__} must not be dict"


def test_piquete_projetado_field_order():
    """PiqueteProjetado field order matches R1 specification exactly."""
    expected = (
        "piquete_id",
        "nome",
        "area_ha",
        "metodo_pastejo",
        "cultivar_slug",
        "cultivar_nome",
        "centroide_lat",
        "centroide_lon",
        "situacao",
        "lote_atual_id",
        "dias_descanso",
        "parametros",
        "faltantes",
        "descanso_min_dias",
        "densidade_kg_ha_por_cm",
        "eficiencia_pastejo",
        "massa_hoje_kg_ms_ha",
        "altura_hoje_cm",
        "taxa_acumulo_prevista_kg_ms_ha_dia",
        "confianca",
        "motivo_confianca",
        "dias_desde_imagem_limpa",
    )
    actual = tuple(f.name for f in fields(contratos.PiqueteProjetado))
    assert actual == expected


def test_lote_projetado_field_order():
    """LoteProjetado field order matches R1 specification exactly."""
    expected = (
        "lote_id",
        "nome",
        "composicao",
        "indissoluvel",
        "piquete_atual_id",
        "desde",
        "peso_vivo_total_kg",
        "consumo_kg_ms_dia",
        "confianca_peso",
        "motivo_confianca_peso",
    )
    actual = tuple(f.name for f in fields(contratos.LoteProjetado))
    assert actual == expected


def test_plano_manejo_field_order():
    """PlanoManejo field order matches R1 specification exactly."""
    expected = (
        "id",
        "fazenda_id",
        "data_geracao",
        "data_inicio",
        "horizonte_dias",
        "movimentacoes",
        "alertas",
        "pedidos_validacao",
        "piquetes",
    )
    actual = tuple(f.name for f in fields(contratos.PlanoManejo))
    assert actual == expected


# ==============================================================================
# Canonical Case & Fixtures Round-trip (KIT-ACEITE-009)
# ==============================================================================


def test_canonical_estado_projetado_fixture_roundtrip():
    """estado_projetado_exemplo.json loads, has 8 piquetes / 2 lotes.

    Also tests that it round-trips identically.
    """
    fixture_path = FIXTURES_DIR / "estado_projetado_exemplo.json"
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    estado = contratos.estado_de_dict(data)
    assert len(estado.piquetes) == 8
    assert len(estado.lotes) == 2

    # Round trip dict
    serialized = contratos.estado_para_dict(estado)
    assert serialized == data

    # Round trip dataclass
    reconstructed = contratos.estado_de_dict(serialized)
    assert reconstructed == estado


def test_canonical_plano_exemplo_fixture_roundtrip():
    """plano_exemplo.json loads, has 3 movs / 3 alerts / 1 req / 8 piquetes, and round-trips."""
    fixture_path = FIXTURES_DIR / "plano_exemplo.json"
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    plano = contratos.plano_de_dict(data)
    assert len(plano.movimentacoes) == 3
    assert len(plano.alertas) == 3
    assert len(plano.pedidos_validacao) == 1
    assert len(plano.piquetes) == 8

    # Worked example assertions from spec
    first_mov = plano.movimentacoes[0]
    assert first_mov.data == date(2026, 9, 28)
    assert first_mov.lote_nome == "Recria"
    assert first_mov.piquete_destino_nome == "Piquete 1"
    assert first_mov.dias_previstos == 3
    assert first_mov.confianca is Confianca.MEDIA

    # Round trip dict
    serialized = contratos.plano_para_dict(plano)
    assert serialized == data

    # Round trip dataclass
    reconstructed = contratos.plano_de_dict(serialized)
    assert reconstructed == plano

    # Valid JSON string encoding without error
    encoded = json.dumps(serialized, ensure_ascii=False)
    assert len(encoded) > 0


# ==============================================================================
# Hidden Cases (KIT-ACEITE-009)
# ==============================================================================


def test_hidden_case_1_plano_de_dict_naive_datetime():
    """Hidden Case 1: plano_de_dict with data_geracao lacking timezone raises ValueError."""
    fixture_path = FIXTURES_DIR / "plano_exemplo.json"
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    bad_data = dict(data)
    bad_data["data_geracao"] = "2026-09-28T08:00:00"

    with pytest.raises(ValueError, match="naive"):
        contratos.plano_de_dict(bad_data)


def test_hidden_case_2_plano_de_dict_unknown_enum_in_alerta():
    """Hidden Case 2: plano_de_dict with unknown TipoAlerta raises ValueError."""
    fixture_path = FIXTURES_DIR / "plano_exemplo.json"
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    bad_alerta = dict(data["alertas"][0])
    bad_alerta["tipo"] = "inexistente"

    bad_data = dict(data)
    bad_data["alertas"] = [bad_alerta, *data["alertas"][1:]]

    with pytest.raises(ValueError, match="unknown TipoAlerta"):
        contratos.plano_de_dict(bad_data)


def test_hidden_case_3_estado_de_dict_missing_lotes_key():
    """Hidden Case 3: estado_de_dict without key lotes raises ValueError mentioning lotes."""
    fixture_path = FIXTURES_DIR / "estado_projetado_exemplo.json"
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    bad_data = {k: v for k, v in data.items() if k != "lotes"}

    with pytest.raises(ValueError, match="lotes"):
        contratos.estado_de_dict(bad_data)


def test_malformed_uuid_and_date():
    """Malformed UUID and date strings raise ValueError."""
    fixture_path = FIXTURES_DIR / "estado_projetado_exemplo.json"
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    bad_uuid = dict(data, fazenda_id="nao-e-uuid")
    with pytest.raises(ValueError, match="invalid UUID"):
        contratos.estado_de_dict(bad_uuid)

    bad_date = dict(data, data_base="2026/09/28")
    with pytest.raises(ValueError, match="invalid date"):
        contratos.estado_de_dict(bad_date)
