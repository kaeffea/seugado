"""Database connection dependency."""

import os
from collections.abc import Iterator
from typing import Annotated, Any

import psycopg
from fastapi import Depends


def obter_conexao() -> Iterator[psycopg.Connection[Any]]:
    """Open one connection per request from DATABASE_URL and always close it."""
    conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=False)
    try:
        yield conn
    finally:
        conn.close()


Conexao = Annotated[psycopg.Connection[Any], Depends(obter_conexao)]
