"""Test doubles shared by the delivery tests."""

import types
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

import psycopg

from seugado.contratos import PlanoManejo
from seugado.delivery.canais.base import Botao


@dataclass(frozen=True)
class Enviado:
    chat_id: int
    texto: str
    botoes: list[list[Botao]]


class CanalFalso:
    """Canal that records what would have reached the producer, and in which order."""

    def __init__(self) -> None:
        self.enviados: list[Enviado] = []
        self.cliques: list[tuple[str, str | None]] = []
        self.ordem: list[str] = []

    def enviar_texto(
        self, chat_id: int, texto: str, botoes: Sequence[Sequence[Botao]] = ()
    ) -> None:
        self.ordem.append("texto")
        self.enviados.append(Enviado(chat_id, texto, [list(linha) for linha in botoes]))

    def responder_clique(self, id_clique: str, texto: str | None = None) -> None:
        self.ordem.append("clique")
        self.cliques.append((id_clique, texto))

    @property
    def textos(self) -> list[str]:
        return [enviado.texto for enviado in self.enviados]


class _CursorFalso:
    def __init__(self, conexao: "ConexaoFalsa") -> None:
        self._conexao = conexao

    def __enter__(self) -> "_CursorFalso":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        self._conexao.consultas.append((sql, params))
        if self._conexao.erro is not None:
            raise self._conexao.erro

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._conexao.linha


class ConexaoFalsa:
    """Answers every query with one fixed row (or none, or raises `erro`); records SQL,
    commits and rollbacks."""

    def __init__(self, linha: tuple[Any, ...] | None, erro: Exception | None = None) -> None:
        self.linha = linha
        self.erro = erro
        self.consultas: list[tuple[str, tuple[Any, ...]]] = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self) -> _CursorFalso:
        return _CursorFalso(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def conexao_falsa(
    linha: tuple[Any, ...] | None, erro: Exception | None = None
) -> tuple[psycopg.Connection[Any], ConexaoFalsa]:
    """The fake typed as a psycopg connection, plus the fake itself for assertions."""
    falsa = ConexaoFalsa(linha, erro)
    return cast("psycopg.Connection[Any]", falsa), falsa


def modulo_falso(nome: str, **atributos: object) -> types.ModuleType:
    """Stand-in for a teammate's module that is not on this branch yet (LEO.md, section 2)."""
    modulo = types.ModuleType(nome)
    modulo.__dict__.update(atributos)
    return modulo


class PlanosFalsos:
    """In-memory persistencia/planos.py following JOAO.md (J4): statuses and answered ids."""

    def __init__(self) -> None:
        self.planos: dict[UUID, PlanoManejo] = {}
        self.status: dict[UUID, str] = {}
        self.respondidas: frozenset[UUID] = frozenset()
        self.promovidos: list[UUID] = []

    def guardar(self, plano: PlanoManejo, status: str) -> None:
        self.planos[plano.id] = plano
        self.status[plano.id] = status

    def _ultimo(self, fazenda_id: UUID, status: str) -> PlanoManejo | None:
        achados = [
            p
            for p in self.planos.values()
            if p.fazenda_id == fazenda_id and self.status[p.id] == status
        ]
        return achados[-1] if achados else None

    def carregar_plano_atual(self, conn: object, fazenda_id: UUID) -> PlanoManejo | None:
        return self._ultimo(fazenda_id, "vigente")

    def carregar_candidato(self, conn: object, fazenda_id: UUID) -> PlanoManejo | None:
        return self._ultimo(fazenda_id, "candidato")

    def carregar_plano(self, conn: object, plano_id: UUID) -> PlanoManejo | None:
        return self.planos.get(plano_id)

    def status_do_plano(self, conn: object, plano_id: UUID) -> str | None:
        return self.status.get(plano_id)

    def promover_candidato(self, conn: object, plano_id: UUID) -> PlanoManejo:
        if self.status.get(plano_id) != "candidato":
            raise ValueError("not a candidate")
        plano = self.planos[plano_id]
        vigente = self._ultimo(plano.fazenda_id, "vigente")
        if vigente is not None:
            self.status[vigente.id] = "substituido"
        self.status[plano_id] = "vigente"
        self.promovidos.append(plano_id)
        return plano

    def descartar_plano(self, conn: object, plano_id: UUID) -> None:
        if self.status.get(plano_id) == "candidato":
            self.status[plano_id] = "descartado"

    def ids_respondidos(self, conn: object, fazenda_id: UUID) -> frozenset[UUID]:
        return self.respondidas

    def modulo(self) -> types.ModuleType:
        nomes = (
            "carregar_plano_atual",
            "carregar_candidato",
            "carregar_plano",
            "status_do_plano",
            "promover_candidato",
            "descartar_plano",
            "ids_respondidos",
        )
        return modulo_falso(
            "seugado.persistencia.planos", **{nome: getattr(self, nome) for nome in nomes}
        )


class CicloFalso:
    """jobs/ciclo.py (Leandro): records each executar_ciclo call, optionally failing."""

    def __init__(self, erro: Exception | None = None) -> None:
        self.erro = erro
        self.chamadas: list[tuple[UUID, dict[str, Any]]] = []

    def executar_ciclo(self, conn: object, fazenda_id: UUID, **opcoes: Any) -> None:
        self.chamadas.append((fazenda_id, opcoes))
        if self.erro is not None:
            raise self.erro

    def modulo(self) -> types.ModuleType:
        return modulo_falso("seugado.jobs.ciclo", executar_ciclo=self.executar_ciclo)
