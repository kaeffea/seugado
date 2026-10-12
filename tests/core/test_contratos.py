"""Smoke checks for cross-module contracts."""

import json
import uuid
from dataclasses import FrozenInstanceError, fields
from datetime import date
from pathlib import Path
from typing import Any, cast

import pytest

from seugado.contratos import (
    DiferencaLote,
    LoteProjetado,
    PassoPlano,
    PiqueteProjetado,
    TipoAlerta,
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


_CAMPOS_ESTRUTURA = ("modulo_id", "praca_id", "praca_lat", "praca_lon")


def _sem_estrutura(dados: dict[str, Any]) -> dict[str, Any]:
    """The same state dict without the SPEC-018 fields (the fixture predates them)."""
    limpo = json.loads(json.dumps(dados))
    for item in (*limpo["piquetes"], *limpo["lotes"]):
        for campo in _CAMPOS_ESTRUTURA:
            item.pop(campo, None)
    return cast("dict[str, Any]", limpo)


def test_estado_fixture_roundtrip() -> None:
    data = _fixture("estado_projetado_exemplo.json")
    estado = estado_de_dict(data)
    assert len(estado.piquetes) == 8
    assert len(estado.lotes) == 2
    assert _sem_estrutura(estado_para_dict(estado)) == data
    assert estado_de_dict(estado_para_dict(estado)) == estado
    json.dumps(estado_para_dict(estado), ensure_ascii=False)


def test_estado_antigo_sem_estrutura_carrega_com_none() -> None:
    """SPEC-018 R1: JSON written before the structure fields still loads, with None."""
    estado = estado_de_dict(_fixture("estado_projetado_exemplo.json"))
    for p in estado.piquetes:
        assert (p.modulo_id, p.praca_id, p.praca_lat, p.praca_lon) == (None, None, None, None)
    assert all(lote.modulo_id is None for lote in estado.lotes)
    escrito = estado_para_dict(estado)
    assert all(campo in escrito["piquetes"][0] for campo in _CAMPOS_ESTRUTURA)
    assert "modulo_id" in escrito["lotes"][0]


def test_estado_estrutura_preenchida_faz_roundtrip() -> None:
    data = _fixture("estado_projetado_exemplo.json")
    modulo, praca = str(uuid.uuid4()), str(uuid.uuid4())
    data["piquetes"][0].update(
        modulo_id=modulo, praca_id=praca, praca_lat=-9.6, praca_lon=-36.0
    )
    data["lotes"][0]["modulo_id"] = modulo
    estado = estado_de_dict(data)
    assert str(estado.piquetes[0].modulo_id) == modulo
    assert (estado.piquetes[0].praca_lat, estado.piquetes[0].praca_lon) == (-9.6, -36.0)
    assert str(estado.lotes[0].modulo_id) == modulo
    assert estado_para_dict(estado)["piquetes"][0]["praca_id"] == praca
    assert estado_de_dict(estado_para_dict(estado)) == estado


def test_estado_chave_ausente_sem_default_continua_erro() -> None:
    data = _fixture("estado_projetado_exemplo.json")
    del data["piquetes"][0]["nome"]
    with pytest.raises(ValueError, match="missing key: 'nome'"):
        estado_de_dict(data)


def test_campos_de_estrutura_ficam_no_fim_com_default_none() -> None:
    piquete = [f.name for f in fields(PiqueteProjetado)]
    assert piquete[-4:] == list(_CAMPOS_ESTRUTURA)
    assert [f.name for f in fields(LoteProjetado)][-1] == "modulo_id"
    for classe, nomes in ((PiqueteProjetado, _CAMPOS_ESTRUTURA), (LoteProjetado, ("modulo_id",))):
        por_nome = {f.name: f for f in fields(classe)}
        assert all(por_nome[n].default is None for n in nomes)


def test_plano_fixture_roundtrip() -> None:
    data = _fixture("plano_exemplo.json")
    plano = plano_de_dict(data)
    assert len(plano.movimentacoes) == 3
    assert len(plano.alertas) == 2
    assert len(plano.pedidos_validacao) == 1
    assert len(plano.piquetes) == 8
    first = plano.movimentacoes[0]
    assert first.data == date(2026, 9, 28)
    assert first.lote_nome == "Recria"
    assert first.piquete_destino_nome == "Piquete 6"
    assert first.dias_previstos == 7
    assert first.confianca is Confianca.MEDIA
    escrito = plano_para_dict(plano)
    for alerta in escrito["alertas"]:  # SPEC-019: always written; the old fixture lacks them
        assert alerta.pop("acao") == ""
        assert alerta.pop("modulo_id") is None
    assert escrito == data
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


def test_alerta_has_thirteen_members_and_diff_dataclasses_are_frozen() -> None:
    assert len(TipoAlerta) == 13  # 9 + abaixo_da_saida, pronto_em, sobra/falta_de_capim (SPEC-019)
    assert TipoAlerta.PASSANDO_DO_PONTO.value == "passando_do_ponto"
    passo = PassoPlano(data=date(2026, 9, 28), piquete_destino_nome="Piquete 1")
    diff = DiferencaLote(
        lote_id=uuid.uuid4(), lote_nome="Recria", antes=(), depois=(passo,)
    )
    assert not hasattr(passo, "__dict__")
    assert not hasattr(diff, "__dict__")
    with pytest.raises(FrozenInstanceError):
        passo.piquete_destino_nome = "x"  # type: ignore[misc]  # intentional: verifying frozen raises
    with pytest.raises(FrozenInstanceError):
        diff.lote_nome = "y"  # type: ignore[misc]  # intentional: verifying frozen raises
