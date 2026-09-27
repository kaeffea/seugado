"""Test doubles shared by the delivery tests."""

import types
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

import psycopg

from seugado.delivery.canais.base import Botao


@dataclass(frozen=True)
class Enviado:
    chat_id: int
    texto: str
    botoes: list[list[Botao]]


class CanalFalso:
    """Canal that records what would have reached the producer."""

    def __init__(self) -> None:
        self.enviados: list[Enviado] = []
        self.cliques: list[tuple[str, str | None]] = []

    def enviar_texto(
        self, chat_id: int, texto: str, botoes: Sequence[Sequence[Botao]] = ()
    ) -> None:
        self.enviados.append(Enviado(chat_id, texto, [list(linha) for linha in botoes]))

    def responder_clique(self, id_clique: str, texto: str | None = None) -> None:
        self.cliques.append((id_clique, texto))


class _CursorFalso:
    def __init__(self, conexao: "ConexaoFalsa") -> None:
        self._conexao = conexao

    def __enter__(self) -> "_CursorFalso":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        self._conexao.consultas.append((sql, params))

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._conexao.linha


class ConexaoFalsa:
    """Answers every query with one fixed row (or none); records the SQL and any commit."""

    def __init__(self, linha: tuple[Any, ...] | None) -> None:
        self.linha = linha
        self.consultas: list[tuple[str, tuple[Any, ...]]] = []
        self.commits = 0

    def cursor(self) -> _CursorFalso:
        return _CursorFalso(self)

    def commit(self) -> None:
        self.commits += 1


def conexao_falsa(linha: tuple[Any, ...] | None) -> tuple[psycopg.Connection[Any], ConexaoFalsa]:
    """The fake typed as a psycopg connection, plus the fake itself for assertions."""
    falsa = ConexaoFalsa(linha)
    return cast("psycopg.Connection[Any]", falsa), falsa


def modulo_falso(nome: str, **atributos: object) -> types.ModuleType:
    """Stand-in for a teammate's module that is not on this branch yet (LEO.md, section 2)."""
    modulo = types.ModuleType(nome)
    modulo.__dict__.update(atributos)
    return modulo
