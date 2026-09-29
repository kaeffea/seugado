"""Lotes routes (owner: Leandro)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from seugado.api.auth import FazendaAutorizada, Usuario
from seugado.api.deps import Conexao
from seugado.cadastro.lotes import (
    LoteIn,
    LoteOut,
    criar_lote,
    dissolver_lote,
    editar_lote,
    listar_lotes,
)

router = APIRouter(tags=["lotes"])


@router.get("/fazendas/{fazenda_id}/lotes", response_model=list[LoteOut])
def listar_lotes_rota(
    fazenda_id: FazendaAutorizada,
    usuario: Usuario,
    conn: Conexao,
) -> list[LoteOut]:
    """Lista os lotes de uma fazenda."""
    return listar_lotes(conn, fazenda_id)


@router.post(
    "/fazendas/{fazenda_id}/lotes",
    response_model=LoteOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_lote_rota(
    fazenda_id: FazendaAutorizada,
    dados: LoteIn,
    usuario: Usuario,
    conn: Conexao,
) -> LoteOut:
    """Cria um novo lote."""
    try:
        lote_id = criar_lote(conn, fazenda_id, str(usuario.id), dados)
        conn.commit()
        # Fetch the newly created lote
        lotes = listar_lotes(conn, fazenda_id)
        for lote in lotes:
            if lote.id == lote_id:
                return lote
        raise HTTPException(status_code=500, detail="Erro ao carregar o lote recém-criado")
    except (ValueError, ValidationError) as e:
        msg = str(e).lower()
        if "ocupado" in msg:
            raise HTTPException(status_code=409, detail=str(e)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/fazendas/{fazenda_id}/lotes/{lote_id}", response_model=LoteOut)
def editar_lote_rota(
    fazenda_id: FazendaAutorizada,
    lote_id: UUID,
    dados: LoteIn,
    usuario: Usuario,
    conn: Conexao,
) -> LoteOut:
    """Edita um lote."""
    try:
        editar_lote(conn, fazenda_id, lote_id, str(usuario.id), dados)
        conn.commit()
        # Fetch the updated lote
        lotes = listar_lotes(conn, fazenda_id)
        for lote in lotes:
            if lote.id == lote_id:
                return lote
        raise HTTPException(status_code=404, detail="Lote não encontrado após edição")
    except (ValueError, ValidationError) as e:
        msg = str(e).lower()
        if "não encontrado" in msg:
            raise HTTPException(status_code=404, detail=str(e)) from e
        if "ocupado" in msg:
            raise HTTPException(status_code=409, detail=str(e)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/fazendas/{fazenda_id}/lotes/{lote_id}", status_code=status.HTTP_204_NO_CONTENT)
def dissolver_lote_rota(
    fazenda_id: FazendaAutorizada,
    lote_id: UUID,
    usuario: Usuario,
    conn: Conexao,
) -> None:
    """Dissolve um lote."""
    try:
        dissolver_lote(conn, fazenda_id, lote_id, str(usuario.id))
        conn.commit()
    except ValueError as e:
        if "não encontrado" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e
