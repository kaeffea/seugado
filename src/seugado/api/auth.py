"""Authentication dependencies."""

import os
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

import httpx
import psycopg
from fastapi import Depends, Header, HTTPException

from seugado.api.deps import Conexao

_HTTP_OK = 200


@dataclass(frozen=True, slots=True)
class UsuarioAtual:
    """Authenticated user resolved from Supabase Auth."""

    id: UUID
    email: str | None


def usuario_atual(
    authorization: Annotated[str | None, Header()] = None,
) -> UsuarioAtual:
    """Resolve the current user through Supabase Auth."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401)
    supabase_url = os.environ["SUPABASE_URL"]
    anon_key = os.environ["SUPABASE_ANON_KEY"]
    response = httpx.get(
        f"{supabase_url}/auth/v1/user",
        headers={"apikey": anon_key, "Authorization": authorization},
        timeout=10.0,
    )
    if response.status_code != _HTTP_OK:
        raise HTTPException(status_code=401)
    body: Any = response.json()
    return UsuarioAtual(id=UUID(body["id"]), email=body.get("email"))


Usuario = Annotated[UsuarioAtual, Depends(usuario_atual)]


def fazenda_do_usuario(conn: psycopg.Connection[Any], usuario_id: UUID) -> UUID | None:
    """Return the farm owned by the user, if any."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT fazenda_id FROM fazenda_usuario WHERE usuario_id = %s",
            (usuario_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    value = row[0]
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def exigir_fazenda(fazenda_id: UUID, usuario: Usuario, conn: Conexao) -> UUID:
    """Ensure the user owns the farm from the path."""
    if fazenda_do_usuario(conn, usuario.id) != fazenda_id:
        raise HTTPException(status_code=403, detail="Sem acesso a esta fazenda")
    return fazenda_id


FazendaAutorizada = Annotated[UUID, Depends(exigir_fazenda)]
