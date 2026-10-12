"""Grazing modules and feeding squares: registration and the farm structure.

This is farm configuration edited in place with UPDATE; nothing here writes to the event log.
"""

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from seugado.planner.estado import UNIDADE_ANIMAL_KG

Conn = psycopg.Connection[Any]


class EmUsoError(Exception):
    """The module or feeding square is still referenced (the route answers 409)."""


class ModuloIn(BaseModel):
    nome: str = Field(..., min_length=1)


class ModuloOut(BaseModel):
    id: UUID
    nome: str
    piquete_ids: list[UUID]
    lote_ids: list[UUID]
    area_ha: float
    ua_total: float
    lotacao_ua_ha: float | None


class PracaIn(BaseModel):
    nome: str = Field(..., min_length=1)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class PracaOut(PracaIn):
    id: UUID


class EstruturaPiqueteIn(BaseModel):
    modulo_id: UUID | None = None
    praca_id: UUID | None = None


class EstruturaPiqueteOut(BaseModel):
    piquete_id: UUID
    modulo_id: UUID | None
    praca_id: UUID | None


class LoteModuloIn(BaseModel):
    modulo_id: UUID | None = None


class LoteModuloOut(BaseModel):
    lote_id: UUID
    modulo_id: UUID | None


class EstruturaFazendaOut(BaseModel):
    piquetes: list[EstruturaPiqueteOut]
    lotes: list[LoteModuloOut]


_NAO_ENCONTRADO = {"modulo": "Módulo não encontrado", "praca": "Praça não encontrada"}


def _sql(conn: Conn, sql: str, params: tuple[Any, ...]) -> tuple[Any, ...] | None:
    """Run one statement; the first row when it returns any (INSERT ... RETURNING, SELECT)."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone() if cur.description else None


def _existe(conn: Conn, sql: str, params: tuple[Any, ...]) -> bool:
    return _sql(conn, sql, params) is not None


def _da_fazenda(conn: Conn, tabela: str, fazenda_id: UUID, linha_id: UUID) -> bool:
    """True when `linha_id` is a row of `tabela` (modulo or praca) of this farm."""
    sql = f"SELECT 1 FROM {tabela} WHERE fazenda_id = %s AND id = %s"
    return _existe(conn, sql, (fazenda_id, linha_id))


def _exigir(conn: Conn, tabela: str, fazenda_id: UUID, linha_id: UUID) -> None:
    if not _da_fazenda(conn, tabela, fazenda_id, linha_id):
        raise LookupError(_NAO_ENCONTRADO[tabela])


def _checar_nome(
    conn: Conn, tabela: str, fazenda_id: UUID, nome: str, ignorar_id: UUID | None = None
) -> None:
    """ValueError for a blank name (it passes `min_length`) or one already used in the farm."""
    if not nome.strip():
        raise ValueError("O nome não pode ficar em branco")
    sql = f"SELECT 1 FROM {tabela} WHERE fazenda_id = %s AND nome = %s AND id IS DISTINCT FROM %s"
    if _existe(conn, sql, (fazenda_id, nome, ignorar_id)):
        artigo = "um módulo" if tabela == "modulo" else "uma praça"
        raise ValueError(f"Já existe {artigo} com esse nome")


def _checar_vinculos(
    conn: Conn, fazenda_id: UUID, modulo_id: UUID | None, praca_id: UUID | None
) -> None:
    """ValueError when the module or square given does not belong to this farm."""
    if modulo_id is not None and not _da_fazenda(conn, "modulo", fazenda_id, modulo_id):
        raise ValueError("Módulo de outra fazenda ou inexistente")
    if praca_id is not None and not _da_fazenda(conn, "praca", fazenda_id, praca_id):
        raise ValueError("Praça de outra fazenda ou inexistente")


# Aggregates always yield one row: a module with no paddock or group gets zeros, not NULLs.
_MODULOS_SQL = """
SELECT m.id, m.nome, p.piquete_ids, l.lote_ids, p.area_ha,
       l.peso_kg / %(ua_kg)s AS ua_total,
       l.peso_kg / %(ua_kg)s / NULLIF(p.area_ha, 0) AS lotacao_ua_ha
FROM modulo m
CROSS JOIN LATERAL (
    SELECT COALESCE(array_agg(ep.piquete_id ORDER BY ep.nome, ep.piquete_id), '{}') AS piquete_ids,
           COALESCE(sum(ep.area_ha), 0) AS area_ha
    FROM piquete_estrutura pe
    JOIN estado_piquete ep ON ep.fazenda_id = pe.fazenda_id AND ep.piquete_id = pe.piquete_id
    WHERE pe.modulo_id = m.id AND pe.fazenda_id = m.fazenda_id AND ep.ativo = TRUE
) p
CROSS JOIN LATERAL (
    SELECT COALESCE(array_agg(el.lote_id ORDER BY el.nome, el.lote_id), '{}') AS lote_ids,
           COALESCE(sum(el.peso_vivo_total_kg), 0) AS peso_kg
    FROM lote_modulo lm
    JOIN estado_lote el ON el.fazenda_id = lm.fazenda_id AND el.lote_id = lm.lote_id
    WHERE lm.modulo_id = m.id AND lm.fazenda_id = m.fazenda_id
) l
WHERE m.fazenda_id = %(fazenda_id)s AND (%(modulo_id)s::uuid IS NULL OR m.id = %(modulo_id)s)
ORDER BY m.nome
"""


def _modulos(conn: Conn, fazenda_id: UUID, modulo_id: UUID | None = None) -> list[ModuloOut]:
    """Modules of the farm (or just one) with active paddocks, groups and stocking rate."""
    params = {"ua_kg": UNIDADE_ANIMAL_KG, "fazenda_id": fazenda_id, "modulo_id": modulo_id}
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_MODULOS_SQL, params)
        return [ModuloOut.model_validate(row) for row in cur.fetchall()]


def listar_modulos(conn: Conn, fazenda_id: UUID) -> list[ModuloOut]:
    """Modules of the farm, ordered by name."""
    return _modulos(conn, fazenda_id)


def criar_modulo(conn: Conn, fazenda_id: UUID, dados: ModuloIn) -> ModuloOut:
    """Create a module; the name must be unique in the farm."""
    _checar_nome(conn, "modulo", fazenda_id, dados.nome)
    sql = "INSERT INTO modulo (fazenda_id, nome) VALUES (%s, %s) RETURNING id"
    row = _sql(conn, sql, (fazenda_id, dados.nome))
    assert row is not None
    return _modulos(conn, fazenda_id, row[0])[0]


def renomear_modulo(conn: Conn, fazenda_id: UUID, modulo_id: UUID, dados: ModuloIn) -> ModuloOut:
    """Rename a module; keeping its own name is allowed."""
    _exigir(conn, "modulo", fazenda_id, modulo_id)
    _checar_nome(conn, "modulo", fazenda_id, dados.nome, modulo_id)
    sql = "UPDATE modulo SET nome = %s WHERE fazenda_id = %s AND id = %s"
    _sql(conn, sql, (dados.nome, fazenda_id, modulo_id))
    return _modulos(conn, fazenda_id, modulo_id)[0]


def excluir_modulo(conn: Conn, fazenda_id: UUID, modulo_id: UUID) -> None:
    """Delete a module that no paddock and no group points to."""
    _exigir(conn, "modulo", fazenda_id, modulo_id)
    em_uso = _existe(
        conn,
        "SELECT 1 FROM piquete_estrutura WHERE modulo_id = %s "
        "UNION ALL SELECT 1 FROM lote_modulo WHERE modulo_id = %s",
        (modulo_id, modulo_id),
    )
    if em_uso:
        raise EmUsoError("Módulo em uso: desvincule piquetes e lotes antes")
    _sql(conn, "DELETE FROM modulo WHERE fazenda_id = %s AND id = %s", (fazenda_id, modulo_id))


def listar_pracas(conn: Conn, fazenda_id: UUID) -> list[PracaOut]:
    """Feeding squares of the farm, ordered by name."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, nome, ST_Y(ponto) AS lat, ST_X(ponto) AS lon FROM praca "
            "WHERE fazenda_id = %s ORDER BY nome",
            (fazenda_id,),
        )
        return [PracaOut.model_validate(row) for row in cur.fetchall()]


def criar_praca(conn: Conn, fazenda_id: UUID, dados: PracaIn) -> PracaOut:
    """Create a feeding square; the name must be unique in the farm."""
    _checar_nome(conn, "praca", fazenda_id, dados.nome)
    row = _sql(
        conn,
        "INSERT INTO praca (fazenda_id, nome, ponto) "
        "VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) RETURNING id",
        (fazenda_id, dados.nome, dados.lon, dados.lat),
    )
    assert row is not None
    return PracaOut(id=row[0], **dados.model_dump())


def editar_praca(conn: Conn, fazenda_id: UUID, praca_id: UUID, dados: PracaIn) -> PracaOut:
    """Change the name and position of a feeding square."""
    _exigir(conn, "praca", fazenda_id, praca_id)
    _checar_nome(conn, "praca", fazenda_id, dados.nome, praca_id)
    _sql(
        conn,
        "UPDATE praca SET nome = %s, ponto = ST_SetSRID(ST_MakePoint(%s, %s), 4326) "
        "WHERE fazenda_id = %s AND id = %s",
        (dados.nome, dados.lon, dados.lat, fazenda_id, praca_id),
    )
    return PracaOut(id=praca_id, **dados.model_dump())


def excluir_praca(conn: Conn, fazenda_id: UUID, praca_id: UUID) -> None:
    """Delete a feeding square that no paddock points to."""
    _exigir(conn, "praca", fazenda_id, praca_id)
    if _existe(conn, "SELECT 1 FROM piquete_estrutura WHERE praca_id = %s", (praca_id,)):
        raise EmUsoError("Praça em uso: desvincule os piquetes antes")
    _sql(conn, "DELETE FROM praca WHERE fazenda_id = %s AND id = %s", (fazenda_id, praca_id))


def definir_estrutura_piquete(
    conn: Conn, fazenda_id: UUID, piquete_id: UUID, dados: EstruturaPiqueteIn
) -> EstruturaPiqueteOut:
    """Set (upsert) the module and feeding square of an active paddock; both None clears it."""
    sql = "SELECT 1 FROM estado_piquete WHERE fazenda_id = %s AND piquete_id = %s AND ativo"
    if not _existe(conn, sql, (fazenda_id, piquete_id)):
        raise LookupError("Piquete não encontrado")
    _checar_vinculos(conn, fazenda_id, dados.modulo_id, dados.praca_id)
    if dados.modulo_id is None and dados.praca_id is None:
        _sql(conn, "DELETE FROM piquete_estrutura WHERE piquete_id = %s", (piquete_id,))
    else:
        _sql(
            conn,
            "INSERT INTO piquete_estrutura (piquete_id, fazenda_id, modulo_id, praca_id) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT (piquete_id) DO UPDATE "
            "SET modulo_id = EXCLUDED.modulo_id, praca_id = EXCLUDED.praca_id",
            (piquete_id, fazenda_id, dados.modulo_id, dados.praca_id),
        )
    return EstruturaPiqueteOut(
        piquete_id=piquete_id, modulo_id=dados.modulo_id, praca_id=dados.praca_id
    )


def definir_modulo_lote(
    conn: Conn, fazenda_id: UUID, lote_id: UUID, dados: LoteModuloIn
) -> LoteModuloOut:
    """Bind a cattle group to a module (upsert), or unbind it with `modulo_id = None`."""
    sql = "SELECT 1 FROM estado_lote WHERE fazenda_id = %s AND lote_id = %s"
    if not _existe(conn, sql, (fazenda_id, lote_id)):
        raise LookupError("Lote não encontrado")
    _checar_vinculos(conn, fazenda_id, dados.modulo_id, None)
    if dados.modulo_id is None:
        _sql(conn, "DELETE FROM lote_modulo WHERE lote_id = %s", (lote_id,))
    else:
        _sql(
            conn,
            "INSERT INTO lote_modulo (lote_id, fazenda_id, modulo_id) VALUES (%s, %s, %s) "
            "ON CONFLICT (lote_id) DO UPDATE SET modulo_id = EXCLUDED.modulo_id",
            (lote_id, fazenda_id, dados.modulo_id),
        )
    return LoteModuloOut(lote_id=lote_id, modulo_id=dados.modulo_id)


def obter_estrutura(conn: Conn, fazenda_id: UUID) -> EstruturaFazendaOut:
    """Structure of every active paddock and every cattle group of the farm."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT ep.piquete_id, pe.modulo_id, pe.praca_id FROM estado_piquete ep "
            "LEFT JOIN piquete_estrutura pe ON pe.piquete_id = ep.piquete_id "
            "WHERE ep.fazenda_id = %s AND ep.ativo ORDER BY ep.nome, ep.piquete_id",
            (fazenda_id,),
        )
        piquetes = [EstruturaPiqueteOut.model_validate(row) for row in cur.fetchall()]
        cur.execute(
            "SELECT el.lote_id, lm.modulo_id FROM estado_lote el "
            "LEFT JOIN lote_modulo lm ON lm.lote_id = el.lote_id "
            "WHERE el.fazenda_id = %s ORDER BY el.nome, el.lote_id",
            (fazenda_id,),
        )
        lotes = [LoteModuloOut.model_validate(row) for row in cur.fetchall()]
    return EstruturaFazendaOut(piquetes=piquetes, lotes=lotes)
