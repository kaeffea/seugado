"""Real-database helpers: a farm shaped like plano_exemplo.json, never committed."""

import os
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest

from seugado.core.models import OrigemEvento, TipoEvento
from seugado.persistencia.eventos import registrar_evento
from seugado.persistencia.projecao_db import reconstruir_projecao

requer_banco = pytest.mark.skipif(
    not os.environ.get("SEUGADO_TEST_DATABASE_URL"), reason="needs SEUGADO_TEST_DATABASE_URL"
)

RECRIA = UUID("22222222-2222-4222-8222-000000000001")
VACAS = UUID("22222222-2222-4222-8222-000000000002")
PIQUETE_INATIVO = 9

_GEOMETRIA = {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}


@dataclass
class Transacoes:
    commits: int = 0
    rollbacks: int = 0


def emular_transacoes(conn: psycopg.Connection[Any]) -> Transacoes:
    """Let code under test commit and roll back inside the test's own transaction.

    commit() keeps the work so far (releases and retakes a savepoint); rollback() goes back
    to the last commit. The fixture's final rollback still discards everything.
    """
    contagem = Transacoes()
    conn.execute("SAVEPOINT codigo_testado")

    def commit() -> None:
        conn.execute("RELEASE SAVEPOINT codigo_testado")
        conn.execute("SAVEPOINT codigo_testado")
        contagem.commits += 1

    def rollback() -> None:
        conn.execute("ROLLBACK TO SAVEPOINT codigo_testado")
        contagem.rollbacks += 1

    conn.commit = commit  # type: ignore[method-assign]
    conn.rollback = rollback  # type: ignore[method-assign]
    return contagem


def piquete(n: int) -> UUID:
    """Id of "Piquete n", the same ids used in plano_exemplo.json."""
    return UUID(f"11111111-1111-4111-8111-{n:012d}")


@dataclass(frozen=True)
class FazendaTeste:
    id: UUID
    chat_id: int | None


def criar_fazenda(conn: psycopg.Connection[Any], com_chat: bool = True) -> FazendaTeste:
    """Piquetes 1-8 active and 9 inactive; Recria in Piquete 2, Vacas com bezerro in Piquete 5."""
    fazenda_id = uuid4()
    chat_id = -random.randint(10**12, 10**13) if com_chat else None  # unique index on it
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO fazenda (id, nome, telegram_chat_id) VALUES (%s, %s, %s)",
            (fazenda_id, "Fazenda Exemplo", chat_id),
        )
    antes = datetime.now(UTC) - timedelta(days=10)

    def registrar(tipo: TipoEvento, payload: dict[str, Any]) -> None:
        registrar_evento(conn, fazenda_id, tipo, OrigemEvento.SISTEMA, antes, payload)

    cultivar_id = uuid4()
    for n in range(1, 10):
        registrar(
            TipoEvento.PIQUETE_CRIADO,
            {
                "entidade_id": piquete(n),
                "nome": f"Piquete {n}",
                "area_ha": 2.0,
                "cultivar_id": cultivar_id,
                "metodo_pastejo": "rotacionado",
                "ativo": n != PIQUETE_INATIVO,
                "geometria_geojson": _GEOMETRIA,
            },
        )
    composicao = [
        {"categoria": "vaca", "n_animais": 20, "peso_medio_kg": 450.0, "origem_peso": "produtor"}
    ]
    for lote_id, nome, n in ((RECRIA, "Recria", 2), (VACAS, "Vacas com bezerro", 5)):
        registrar(
            TipoEvento.LOTE_CRIADO,
            {"entidade_id": lote_id, "nome": nome, "composicao": composicao, "indissoluvel": False},
        )
        registrar(
            TipoEvento.MANEJO_CONFIRMADO,
            {
                "entidade_id": uuid4(),
                "lote_id": lote_id,
                "piquete_destino_id": piquete(n),
                "data_execucao": antes.date(),
            },
        )
    reconstruir_projecao(conn, fazenda_id)
    return FazendaTeste(fazenda_id, chat_id)
