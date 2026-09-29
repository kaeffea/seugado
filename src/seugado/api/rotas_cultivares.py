"""Cultivares routes."""

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from seugado.api.auth import Usuario
from seugado.api.deps import Conexao
from seugado.core.models import MetodoPastejo
from seugado.persistencia.catalogo import carregar_catalogo, faltantes_calibracao

router = APIRouter(tags=["cultivares"])


class CultivarOut(BaseModel):
    """Cultivar public model (mirrors the Cultivar interface in frontend/src/lib/tipos.ts)."""

    id: UUID
    slug: str
    nome: str
    regimes_disponiveis: list[str]
    calibrada: bool
    faltantes_calibracao: list[str]


@router.get("/cultivares", response_model=list[CultivarOut])
def api_listar_cultivares(usuario: Usuario, conn: Conexao) -> list[CultivarOut]:
    """List all grass cultivars in the catalog, sorted by name, with calibration gaps."""
    catalogo = carregar_catalogo(conn, fazenda_id=None)
    saida: list[CultivarOut] = []
    for c in sorted(catalogo.values(), key=lambda c: c.nome):
        faltantes = list(faltantes_calibracao(c, MetodoPastejo.ROTACIONADO))
        saida.append(
            CultivarOut(
                id=c.id,
                slug=c.slug,
                nome=c.nome,
                regimes_disponiveis=[b.metodo.value for b in c.parametros_por_regime],
                calibrada=not faltantes,
                faltantes_calibracao=faltantes,
            )
        )
    return saida
