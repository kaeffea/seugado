"""Cultivares routes."""

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from seugado.api.auth import Usuario
from seugado.api.deps import Conexao
from seugado.persistencia.catalogo import carregar_catalogo

router = APIRouter(tags=["cultivares"])


class CultivarOut(BaseModel):
    """Cultivar public model."""

    id: UUID
    slug: str
    nome: str


@router.get("/cultivares", response_model=list[CultivarOut])
def api_listar_cultivares(usuario: Usuario, conn: Conexao) -> list[CultivarOut]:
    """List all available grass cultivars in the catalog."""
    catalogo = carregar_catalogo(conn, fazenda_id=None)
    return [
        CultivarOut(id=c.id, slug=c.slug, nome=c.nome)
        for c in catalogo.values()
    ]
