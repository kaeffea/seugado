import os
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest

from seugado.core.models import OrigemEvento, TipoEvento
from seugado.persistencia.eventos import registrar_evento
from seugado.persistencia.projecao_db import carregar_eventos, reconstruir_projecao

pytestmark = pytest.mark.skipif(
    not os.environ.get("SEUGADO_TEST_DATABASE_URL"),
    reason="needs SEUGADO_TEST_DATABASE_URL",
)

GEOMETRIA = {
    "type": "Polygon",
    "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
}


def _conectar() -> psycopg.Connection[Any]:
    return psycopg.connect(os.environ["SEUGADO_TEST_DATABASE_URL"])


def _fazenda(conn: psycopg.Connection[Any]) -> uuid.UUID:
    fazenda_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO fazenda (id) VALUES (%s)", (fazenda_id,))
    return fazenda_id


def _registrar(
    conn: psycopg.Connection[Any],
    fazenda_id: uuid.UUID,
    tipo: TipoEvento,
    dia: int,
    payload: dict[str, Any],
) -> uuid.UUID:
    return registrar_evento(
        conn,
        fazenda_id,
        tipo,
        OrigemEvento.SISTEMA,
        datetime(2026, 9, dia, 9, 0, tzinfo=UTC),
        payload,
    )


def _piquete(
    conn: psycopg.Connection[Any],
    fazenda_id: uuid.UUID,
    piquete_id: uuid.UUID,
    cultivar_id: uuid.UUID,
) -> None:
    _registrar(
        conn,
        fazenda_id,
        TipoEvento.PIQUETE_CRIADO,
        1,
        {
            "entidade_id": piquete_id,
            "nome": "Piquete 7",
            "area_ha": 5.81,
            "cultivar_id": cultivar_id,
            "metodo_pastejo": "rotacionado",
            "ativo": True,
            "geometria_geojson": GEOMETRIA,
        },
    )


def _lote(conn: psycopg.Connection[Any], fazenda_id: uuid.UUID, lote_id: uuid.UUID) -> None:
    _registrar(
        conn,
        fazenda_id,
        TipoEvento.LOTE_CRIADO,
        2,
        {
            "entidade_id": lote_id,
            "nome": "Lote A",
            "composicao": [
                {
                    "categoria": "novilho",
                    "n_animais": 40,
                    "peso_medio_kg": 337.5,
                    "origem_peso": "ua_tabela",
                }
            ],
            "indissoluvel": False,
        },
    )


def test_carregar_eventos_ordena_e_mapeia():
    conn = _conectar()
    try:
        fazenda_id = _fazenda(conn)
        piquete_id, cultivar_id = uuid.uuid4(), uuid.uuid4()
        _registrar(
            conn,
            fazenda_id,
            TipoEvento.PIQUETE_CRIADO,
            10,
            {
                "entidade_id": piquete_id,
                "nome": "Tarde",
                "area_ha": 2.0,
                "cultivar_id": cultivar_id,
                "metodo_pastejo": "continuo",
                "ativo": True,
                "geometria_geojson": GEOMETRIA,
            },
        )
        _registrar(
            conn,
            fazenda_id,
            TipoEvento.LOTE_CRIADO,
            5,
            {
                "entidade_id": uuid.uuid4(),
                "nome": "Cedo",
                "composicao": [
                    {
                        "categoria": "adulto",
                        "n_animais": 10,
                        "peso_medio_kg": 450.0,
                        "origem_peso": "produtor",
                    }
                ],
                "indissoluvel": False,
            },
        )
        eventos = carregar_eventos(conn, fazenda_id)
        assert [e.tipo for e in eventos] == [TipoEvento.LOTE_CRIADO, TipoEvento.PIQUETE_CRIADO]
        assert eventos[0].origem == OrigemEvento.SISTEMA
        assert eventos[0].payload["nome"] == "Cedo"
        assert eventos[0].ocorrido_em < eventos[1].ocorrido_em
    finally:
        conn.rollback()
        conn.close()


def test_reconstruir_escreve_derivadas_sem_commit():
    conn = _conectar()
    try:
        fazenda_id = _fazenda(conn)
        piquete_id, lote_id, cultivar_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        _piquete(conn, fazenda_id, piquete_id, cultivar_id)
        _lote(conn, fazenda_id, lote_id)
        _registrar(
            conn,
            fazenda_id,
            TipoEvento.MANEJO_CONFIRMADO,
            10,
            {
                "entidade_id": uuid.uuid4(),
                "lote_id": lote_id,
                "piquete_destino_id": piquete_id,
                "data_execucao": "2026-09-10",
            },
        )
        _registrar(
            conn,
            fazenda_id,
            TipoEvento.LEITURA_SATELITE,
            11,
            {
                "entidade_id": uuid.uuid4(),
                "piquete_id": piquete_id,
                "data": "2026-09-11",
                "ndvi": 0.62,
                "refletancia_red": 0.08,
                "refletancia_nir": 0.35,
                "origem_ndvi": "optico",
                "pct_nuvem": 5.0,
                "pixels_validos": 340,
            },
        )
        _registrar(
            conn,
            fazenda_id,
            TipoEvento.ALTURA_MEDIDA,
            12,
            {
                "entidade_id": uuid.uuid4(),
                "piquete_id": piquete_id,
                "data": "2026-09-12",
                "altura_cm": 28.0,
                "meio": "bot",
            },
        )
        estado = reconstruir_projecao(conn, fazenda_id)
        assert estado.piquetes[piquete_id].lote_atual_id == lote_id
        assert estado.alturas[piquete_id].altura_cm == 28.0
        seq = max(e.sequencia for e in carregar_eventos(conn, fazenda_id))
        with conn.cursor() as cur:
            cur.execute(
                "SELECT situacao, derivado_ate_sequencia,"
                " ST_GeometryType(geometria), ST_SRID(geometria)"
                " FROM estado_piquete WHERE fazenda_id = %s AND piquete_id = %s",
                (fazenda_id, piquete_id),
            )
            assert cur.fetchone() == ("ocupado", seq, "ST_Polygon", 4326)
            cur.execute(
                "SELECT composicao, peso_vivo_total_kg FROM estado_lote"
                " WHERE fazenda_id = %s AND lote_id = %s",
                (fazenda_id, lote_id),
            )
            linha = cur.fetchone()
            assert linha is not None
            composicao, peso = linha
            assert composicao[0]["origem_peso"] == "ua_tabela"
            assert peso == pytest.approx(40 * 337.5)
            cur.execute("SELECT ndvi, origem FROM leitura WHERE fazenda_id = %s", (fazenda_id,))
            assert cur.fetchone() == (0.62, "optico")
            cur.execute(
                "SELECT altura_cm, meio FROM altura_atual WHERE fazenda_id = %s", (fazenda_id,)
            )
            assert cur.fetchone() == (28.0, "bot")
        probe = _conectar()
        try:
            with probe.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM estado_piquete WHERE fazenda_id = %s", (fazenda_id,)
                )
                row = cur.fetchone()
                assert row is not None and row[0] == 0  # uncommitted: invisible
        finally:
            probe.close()
    finally:
        conn.rollback()
        conn.close()


def test_reconstruir_fazenda_vazia_limpa_derivadas():
    conn = _conectar()
    try:
        fazenda_id = _fazenda(conn)
        piquete_id = uuid.uuid4()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO altura_atual "
                "(fazenda_id, piquete_id, data, altura_cm, meio, derivado_ate_sequencia) "
                "VALUES (%s, %s, CURRENT_DATE, 25.0, 'bot', 1)",
                (fazenda_id, piquete_id),
            )
        estado = reconstruir_projecao(conn, fazenda_id)
        assert estado.piquetes == {} and estado.lotes == {}
        assert estado.leituras == {} and estado.alturas == {}
        consultas = (
            "SELECT count(*) FROM estado_piquete WHERE fazenda_id = %s",
            "SELECT count(*) FROM estado_lote WHERE fazenda_id = %s",
            "SELECT count(*) FROM leitura WHERE fazenda_id = %s",
            "SELECT count(*) FROM altura_atual WHERE fazenda_id = %s",
        )
        with conn.cursor() as cur:
            for sql in consultas:
                cur.execute(sql, (fazenda_id,))
                row = cur.fetchone()
                assert row is not None and row[0] == 0
    finally:
        conn.rollback()
        conn.close()
