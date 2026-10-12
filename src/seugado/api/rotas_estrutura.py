"""Grazing module and feeding square routes."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from seugado.api.auth import FazendaAutorizada
from seugado.api.deps import Conexao
from seugado.cadastro import estrutura as est

router = APIRouter(tags=["estrutura"])


@contextmanager
def _transacao(conn: psycopg.Connection[Any]) -> Iterator[None]:
    """Commit on success; roll back and map domain errors to HTTP errors."""
    try:
        yield
        conn.commit()
    except LookupError as e:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (ValueError, ValidationError) as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    except est.EmUsoError as e:
        conn.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception:
        conn.rollback()
        raise


@router.get("/fazendas/{fazenda_id}/modulos", response_model=list[est.ModuloOut])
def api_listar_modulos(fazenda_id: FazendaAutorizada, conn: Conexao) -> list[est.ModuloOut]:
    return est.listar_modulos(conn, fazenda_id)


@router.post("/fazendas/{fazenda_id}/modulos", response_model=est.ModuloOut, status_code=201)
def api_criar_modulo(
    dados: est.ModuloIn, fazenda_id: FazendaAutorizada, conn: Conexao
) -> est.ModuloOut:
    with _transacao(conn):
        return est.criar_modulo(conn, fazenda_id, dados)


@router.put("/fazendas/{fazenda_id}/modulos/{modulo_id}", response_model=est.ModuloOut)
def api_renomear_modulo(
    modulo_id: UUID, dados: est.ModuloIn, fazenda_id: FazendaAutorizada, conn: Conexao
) -> est.ModuloOut:
    with _transacao(conn):
        return est.renomear_modulo(conn, fazenda_id, modulo_id, dados)


@router.delete("/fazendas/{fazenda_id}/modulos/{modulo_id}", status_code=204)
def api_excluir_modulo(modulo_id: UUID, fazenda_id: FazendaAutorizada, conn: Conexao) -> None:
    with _transacao(conn):
        est.excluir_modulo(conn, fazenda_id, modulo_id)


@router.get("/fazendas/{fazenda_id}/pracas", response_model=list[est.PracaOut])
def api_listar_pracas(fazenda_id: FazendaAutorizada, conn: Conexao) -> list[est.PracaOut]:
    return est.listar_pracas(conn, fazenda_id)


@router.post("/fazendas/{fazenda_id}/pracas", response_model=est.PracaOut, status_code=201)
def api_criar_praca(
    dados: est.PracaIn, fazenda_id: FazendaAutorizada, conn: Conexao
) -> est.PracaOut:
    with _transacao(conn):
        return est.criar_praca(conn, fazenda_id, dados)


@router.put("/fazendas/{fazenda_id}/pracas/{praca_id}", response_model=est.PracaOut)
def api_editar_praca(
    praca_id: UUID, dados: est.PracaIn, fazenda_id: FazendaAutorizada, conn: Conexao
) -> est.PracaOut:
    with _transacao(conn):
        return est.editar_praca(conn, fazenda_id, praca_id, dados)


@router.delete("/fazendas/{fazenda_id}/pracas/{praca_id}", status_code=204)
def api_excluir_praca(praca_id: UUID, fazenda_id: FazendaAutorizada, conn: Conexao) -> None:
    with _transacao(conn):
        est.excluir_praca(conn, fazenda_id, praca_id)


@router.get("/fazendas/{fazenda_id}/estrutura", response_model=est.EstruturaFazendaOut)
def api_obter_estrutura(fazenda_id: FazendaAutorizada, conn: Conexao) -> est.EstruturaFazendaOut:
    return est.obter_estrutura(conn, fazenda_id)


@router.put(
    "/fazendas/{fazenda_id}/piquetes/{piquete_id}/estrutura",
    response_model=est.EstruturaPiqueteOut,
)
def api_definir_estrutura_piquete(
    piquete_id: UUID,
    dados: est.EstruturaPiqueteIn,
    fazenda_id: FazendaAutorizada,
    conn: Conexao,
) -> est.EstruturaPiqueteOut:
    with _transacao(conn):
        return est.definir_estrutura_piquete(conn, fazenda_id, piquete_id, dados)


@router.put("/fazendas/{fazenda_id}/lotes/{lote_id}/modulo", response_model=est.LoteModuloOut)
def api_definir_modulo_lote(
    lote_id: UUID, dados: est.LoteModuloIn, fazenda_id: FazendaAutorizada, conn: Conexao
) -> est.LoteModuloOut:
    with _transacao(conn):
        return est.definir_modulo_lote(conn, fazenda_id, lote_id, dados)
