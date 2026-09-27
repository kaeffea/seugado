"""Smoke checks for cross-module contracts."""

import json
from datetime import date
from pathlib import Path
from typing import Any, cast

import pytest

from seugado.contratos import (
    estado_de_dict,
    estado_para_dict,
    plano_de_dict,
    plano_para_dict,
)
from seugado.core.models import Confianca


def _fixture(name: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "fixtures" / name
    with path.open(encoding="utf-8") as f:
        return cast("dict[str, Any]", json.load(f))


def test_estado_fixture_roundtrip() -> None:
    data = _fixture("estado_projetado_exemplo.json")
    estado = estado_de_dict(data)
    assert len(estado.piquetes) == 8
    assert len(estado.lotes) == 2
    assert estado_para_dict(estado) == data
    assert estado_de_dict(estado_para_dict(estado)) == estado
    json.dumps(estado_para_dict(estado), ensure_ascii=False)


def test_plano_fixture_roundtrip() -> None:
    data = _fixture("plano_exemplo.json")
    plano = plano_de_dict(data)
    assert len(plano.movimentacoes) == 3
    assert len(plano.alertas) == 3
    assert len(plano.pedidos_validacao) == 1
    assert len(plano.piquetes) == 8
    first = plano.movimentacoes[0]
    assert first.data == date(2026, 9, 28)
    assert first.lote_nome == "Recria"
    assert first.piquete_destino_nome == "Piquete 1"
    assert first.dias_previstos == 3
    assert first.confianca is Confianca.MEDIA
    assert plano_para_dict(plano) == data
    assert plano_de_dict(plano_para_dict(plano)) == plano
    json.dumps(plano_para_dict(plano), ensure_ascii=False)


def test_plano_rejects_bad_values() -> None:
    data = _fixture("plano_exemplo.json")
    naive = dict(data, data_geracao="2026-09-28T08:00:00")
    with pytest.raises(ValueError):
        plano_de_dict(naive)
    missing = dict(data)
    del missing["id"]
    with pytest.raises(ValueError):
        plano_de_dict(missing)
    bad_enum = dict(data["movimentacoes"][0], confianca="enorme")
    bad = dict(data, movimentacoes=[bad_enum, *data["movimentacoes"][1:]])
    with pytest.raises(ValueError):
        plano_de_dict(bad)


def test_estado_rejects_bad_uuid() -> None:
    data = _fixture("estado_projetado_exemplo.json")
    bad = dict(data, fazenda_id="not-a-uuid")
    with pytest.raises(ValueError):
        estado_de_dict(bad)
