"""J4: plan storage with status. Every test runs inside one transaction that is rolled back."""

import json
import os
import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import pytest

from seugado.contratos import PlanoManejo, plano_de_dict
from seugado.core.models import OrigemEvento, TipoEvento
from seugado.persistencia.eventos import registrar_evento
from seugado.persistencia.planos import (
    carregar_candidato,
    carregar_plano,
    carregar_plano_atual,
    descartar_plano,
    ids_respondidos,
    promover_candidato,
    salvar_plano,
    status_do_plano,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("SEUGADO_TEST_DATABASE_URL"),
    reason="needs SEUGADO_TEST_DATABASE_URL",
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "plano_exemplo.json"


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[Any]]:
    c = psycopg.connect(os.environ["SEUGADO_TEST_DATABASE_URL"], autocommit=False)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


@pytest.fixture
def fazenda_id(conn: psycopg.Connection[Any]) -> UUID:
    fid = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO fazenda (id) VALUES (%s)", (fid,))
    return fid


def _plano(fazenda_id: UUID, gerado_em: datetime | None = None) -> PlanoManejo:
    base = plano_de_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))
    plano_id = uuid.uuid4()
    movs = tuple(replace(m, id=uuid.uuid5(plano_id, str(m.id))) for m in base.movimentacoes)
    return replace(
        base,
        id=plano_id,
        fazenda_id=fazenda_id,
        data_geracao=gerado_em or base.data_geracao,
        movimentacoes=movs,
    )


def _recomendacoes(conn: psycopg.Connection[Any], fazenda_id: UUID) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM evento WHERE fazenda_id = %s AND tipo = %s",
            (fazenda_id, TipoEvento.MANEJO_RECOMENDADO.value),
        )
        row = cur.fetchone()
    assert row is not None
    return int(row[0])


def _vigentes(conn: psycopg.Connection[Any], fazenda_id: UUID) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM plano WHERE fazenda_id = %s AND status = 'vigente'",
            (fazenda_id,),
        )
        row = cur.fetchone()
    assert row is not None
    return int(row[0])


def test_salvar_e_carregar_devolve_plano_igual(
    conn: psycopg.Connection[Any], fazenda_id: UUID
) -> None:
    plano = _plano(fazenda_id)
    assert plano.movimentacoes  # the fixture has movements, so events are exercised
    salvar_plano(conn, plano)
    assert carregar_plano_atual(conn, fazenda_id) == plano
    assert carregar_plano(conn, plano.id) == plano
    assert status_do_plano(conn, plano.id) == "vigente"
    assert status_do_plano(conn, uuid.uuid4()) is None


def test_vigente_novo_substitui_o_anterior(
    conn: psycopg.Connection[Any], fazenda_id: UUID
) -> None:
    primeiro = _plano(fazenda_id, datetime(2026, 9, 21, 8, 0, tzinfo=UTC))
    segundo = _plano(fazenda_id, datetime(2026, 9, 28, 8, 0, tzinfo=UTC))
    salvar_plano(conn, primeiro)
    salvar_plano(conn, segundo)
    assert _vigentes(conn, fazenda_id) == 1
    assert carregar_plano_atual(conn, fazenda_id) == segundo
    assert status_do_plano(conn, primeiro.id) == "substituido"


def test_candidato_nao_gera_evento_e_promover_gera(
    conn: psycopg.Connection[Any], fazenda_id: UUID
) -> None:
    vigente = _plano(fazenda_id, datetime(2026, 9, 28, 8, 0, tzinfo=UTC))
    salvar_plano(conn, vigente)
    eventos_vigente = _recomendacoes(conn, fazenda_id)
    assert eventos_vigente == len(vigente.movimentacoes)

    candidato = _plano(fazenda_id, datetime(2026, 9, 30, 8, 0, tzinfo=UTC))
    salvar_plano(conn, candidato, "candidato")
    assert _recomendacoes(conn, fazenda_id) == eventos_vigente
    assert carregar_candidato(conn, fazenda_id) == candidato
    assert carregar_plano_atual(conn, fazenda_id) == vigente

    promovido = promover_candidato(conn, candidato.id)
    assert promovido == candidato
    assert _recomendacoes(conn, fazenda_id) == eventos_vigente + len(candidato.movimentacoes)
    assert status_do_plano(conn, candidato.id) == "vigente"
    assert status_do_plano(conn, vigente.id) == "substituido"
    assert _vigentes(conn, fazenda_id) == 1
    assert carregar_candidato(conn, fazenda_id) is None

    with pytest.raises(ValueError):
        promover_candidato(conn, candidato.id)  # no longer a candidato


def test_descartar_candidato(conn: psycopg.Connection[Any], fazenda_id: UUID) -> None:
    salvar_plano(conn, _plano(fazenda_id))
    candidato = _plano(fazenda_id, datetime(2026, 9, 30, 8, 0, tzinfo=UTC))
    salvar_plano(conn, candidato, "candidato")
    descartar_plano(conn, candidato.id)
    assert status_do_plano(conn, candidato.id) == "descartado"
    assert carregar_candidato(conn, fazenda_id) is None


def test_ids_respondidos(conn: psycopg.Connection[Any], fazenda_id: UUID) -> None:
    plano = _plano(fazenda_id)
    salvar_plano(conn, plano)
    assert ids_respondidos(conn, fazenda_id) == frozenset()
    mov = plano.movimentacoes[0]
    registrar_evento(
        conn,
        fazenda_id,
        TipoEvento.MANEJO_RECUSADO,
        OrigemEvento.PRODUTOR,
        ocorrido_em=datetime.now(UTC),
        payload={"entidade_id": str(mov.id), "motivo": None},
    )
    assert ids_respondidos(conn, fazenda_id) == frozenset({mov.id})
