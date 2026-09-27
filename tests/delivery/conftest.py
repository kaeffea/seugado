"""Shared fixtures for the delivery tests, which never reach the real Telegram API."""

import json
from pathlib import Path

import httpx
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
