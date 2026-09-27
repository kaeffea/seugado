"""Shared fixtures for the delivery tests, which never reach the real Telegram API."""

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest

from seugado.contratos import PlanoManejo, plano_de_dict


@pytest.fixture(autouse=True)
def _sem_rede(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any test that calls httpx without installing its own fake first."""

    def _bloqueado(*args: object, **kwargs: object) -> httpx.Response:
        raise AssertionError("delivery tests must not call the network: patch httpx.post")

    monkeypatch.setattr(httpx, "post", _bloqueado)
    monkeypatch.setattr(httpx, "get", _bloqueado)


@pytest.fixture
def plano() -> PlanoManejo:
    """tests/fixtures/plano_exemplo.json as a PlanoManejo."""
    path = Path(__file__).resolve().parents[1] / "fixtures" / "plano_exemplo.json"
    with path.open(encoding="utf-8") as f:
        return plano_de_dict(json.load(f))


@pytest.fixture
def conn_banco() -> Iterator[psycopg.Connection[Any]]:
    """Real test-database connection, always rolled back.

    The database is shared and `evento` is append-only, so a committed test row could never
    be removed: commit() fails here. Tests of code that commits replace it with a counter.
    """
    conn = psycopg.connect(os.environ["SEUGADO_TEST_DATABASE_URL"])

    def _commit_proibido() -> None:
        raise AssertionError("tests must not commit to the shared database")

    conn.commit = _commit_proibido  # type: ignore[method-assign]
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
