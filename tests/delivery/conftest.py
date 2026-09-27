"""Delivery tests never reach the real Telegram API."""

import httpx
import pytest


@pytest.fixture(autouse=True)
def _sem_rede(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any test that calls httpx without installing its own fake first."""

    def _bloqueado(*args: object, **kwargs: object) -> httpx.Response:
        raise AssertionError("delivery tests must not call the network: patch httpx.post")

    monkeypatch.setattr(httpx, "post", _bloqueado)
    monkeypatch.setattr(httpx, "get", _bloqueado)
