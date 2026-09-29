"""Authentication dependencies."""

import os
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

import httpx
import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from seugado.api.deps import Conexao

_HTTP_OK = 200

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

router = APIRouter(tags=["auth"])


class Token(BaseModel):
    """OAuth2 token response."""

    access_token: str
    token_type: str = "bearer"


@router.post("/auth/token", response_model=Token)
def obter_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> dict[str, str]:
    """Exchange username (email) and password for a Supabase access token."""
    supabase_url = os.environ["SUPABASE_URL"]
    anon_key = os.environ["SUPABASE_ANON_KEY"]
    response = httpx.post(
        f"{supabase_url}/auth/v1/token?grant_type=password",
        headers={"apikey": anon_key},
        json={"email": form_data.username, "password": form_data.password},
        timeout=10.0,
    )
    if response.status_code != _HTTP_OK:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    body: Any = response.json()
    return {
        "access_token": str(body["access_token"]),
        "token_type": "bearer",
    }


@dataclass(frozen=True, slots=True)
class UsuarioAtual:
    """Authenticated user resolved from Supabase Auth."""

    id: UUID
    email: str | None


def usuario_atual(
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> UsuarioAtual:
    """Resolve the current user through Supabase Auth."""
    if token is None or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if token.startswith("Token "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    token_puro = token.removeprefix("Bearer ").strip()
    if not token_puro:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    supabase_url = os.environ["SUPABASE_URL"]
    anon_key = os.environ["SUPABASE_ANON_KEY"]
    response = httpx.get(
        f"{supabase_url}/auth/v1/user",
        headers={"apikey": anon_key, "Authorization": f"Bearer {token_puro}"},
        timeout=10.0,
    )
    if response.status_code != _HTTP_OK:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
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
    """Ensure the farm exists; every authenticated user is an admin."""
    _ = usuario  # required dependency so anonymous calls still get 401
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM fazenda WHERE id = %s", (fazenda_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Fazenda não encontrada")
    return fazenda_id


FazendaAutorizada = Annotated[UUID, Depends(exigir_fazenda)]
