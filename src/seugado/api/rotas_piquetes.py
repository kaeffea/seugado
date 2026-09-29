"""Piquetes routes (owner: Ezequiel)."""
# ruff: noqa: B008

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from seugado.api.auth import FazendaAutorizada, Usuario
from seugado.api.deps import Conexao
from seugado.cadastro.piquetes import (
    AlturaIn,
    PiqueteIn,
    PiqueteOut,
    criar_piquete,
    desativar_piquete,
    editar_piquete,
    listar_piquetes,
    registrar_altura,
)

router = APIRouter(tags=["piquetes"])


@router.get("/fazendas/{fazenda_id}/piquetes", response_model=list[PiqueteOut])
def api_listar_piquetes(
    fazenda_id: FazendaAutorizada,
    conn: Conexao,
) -> list[PiqueteOut]:
    return listar_piquetes(conn, fazenda_id)


@router.post("/fazendas/{fazenda_id}/piquetes", response_model=PiqueteOut, status_code=201)
def api_criar_piquete(
    dados: PiqueteIn,
    fazenda_id: FazendaAutorizada,
    usuario: Usuario,
    conn: Conexao,
) -> PiqueteOut:
    try:
        pid = criar_piquete(conn, fazenda_id, usuario.id, dados)
        conn.commit()
    except (ValueError, ValidationError) as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e

    for p in listar_piquetes(conn, fazenda_id):
        if p.id == pid:
            return p
    raise HTTPException(status_code=404, detail="Criou mas não listou")


@router.put("/fazendas/{fazenda_id}/piquetes/{piquete_id}", response_model=PiqueteOut)
def api_editar_piquete(
    piquete_id: UUID,
    dados: PiqueteIn,
    fazenda_id: FazendaAutorizada,
    usuario: Usuario,
    conn: Conexao,
) -> PiqueteOut:
    try:
        editar_piquete(conn, fazenda_id, piquete_id, usuario.id, dados)
        conn.commit()
    except LookupError as e:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (ValueError, ValidationError) as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e

    for p in listar_piquetes(conn, fazenda_id):
        if p.id == piquete_id:
            return p
    raise HTTPException(status_code=404, detail="Editou mas sumiu")


@router.delete("/fazendas/{fazenda_id}/piquetes/{piquete_id}", status_code=204)
def api_desativar_piquete(
    piquete_id: UUID,
    fazenda_id: FazendaAutorizada,
    usuario: Usuario,
    conn: Conexao,
) -> None:
    try:
        desativar_piquete(conn, fazenda_id, piquete_id, usuario.id)
        conn.commit()
    except LookupError as e:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        conn.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/fazendas/{fazenda_id}/piquetes/{piquete_id}/alturas", status_code=201)
def api_registrar_altura(
    piquete_id: UUID,
    dados: AlturaIn,
    fazenda_id: FazendaAutorizada,
    usuario: Usuario,
    conn: Conexao,
) -> None:
    try:
        registrar_altura(conn, fazenda_id, piquete_id, usuario.id, dados)
        conn.commit()
    except LookupError as e:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (ValueError, ValidationError) as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e

