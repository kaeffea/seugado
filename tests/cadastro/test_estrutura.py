"""Smoke tests for modules and feeding squares (SPEC-017).

The database tests write derived rows directly inside the test transaction, which is rolled
back at the end, so the shared database is never changed.
"""

from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from pydantic import ValidationError

from seugado.cadastro.clientes import ClienteIn, criar_cliente
from seugado.cadastro.estrutura import (
    EmUsoError,
    EstruturaPiqueteIn,
    LoteModuloIn,
    ModuloIn,
    PracaIn,
    criar_modulo,
    criar_praca,
    definir_estrutura_piquete,
    definir_modulo_lote,
    editar_praca,
    excluir_modulo,
    excluir_praca,
    listar_modulos,
    listar_pracas,
    obter_estrutura,
    renomear_modulo,
)
from seugado.cadastro.fazenda import FazendaIn, criar_fazenda


def _fazenda(conn: psycopg.Connection[Any], nome: str = "Fazenda Estrutura") -> UUID:
    cliente = criar_cliente(conn, ClienteIn(nome=f"Cliente {nome}"))
    return criar_fazenda(
        conn,
        FazendaIn(
            cliente_id=cliente.id,
            nome=nome,
            funcionarios_disponiveis=1,
            animais_por_funcionario_dia=100,
            dias_preferenciais_manejo=[0],
            envio_plano_dia=0,
            envio_plano_hora=6,
        ),
    )


def _piquete(
    conn: psycopg.Connection[Any], fazenda_id: UUID, nome: str, area_ha: float, ativo: bool = True
) -> UUID:
    piquete_id = uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO estado_piquete (
                fazenda_id, piquete_id, nome, area_ha, cultivar_id, metodo_pastejo, ativo,
                geometria, situacao, desde, dias_descanso, derivado_ate_sequencia
            ) VALUES (
                %s, %s, %s, %s, %s, 'rotacionado', %s,
                ST_GeomFromText('POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))', 4326),
                'descansando', CURRENT_DATE, 0, 0
            )
            """,
            (fazenda_id, piquete_id, nome, area_ha, uuid4(), ativo),
        )
    return piquete_id


def _lote(conn: psycopg.Connection[Any], fazenda_id: UUID, nome: str, peso_kg: float) -> UUID:
    lote_id = uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO estado_lote (
                fazenda_id, lote_id, nome, indissoluvel, composicao,
                peso_vivo_total_kg, derivado_ate_sequencia
            ) VALUES (%s, %s, %s, FALSE, '[]'::jsonb, %s, 0)
            """,
            (fazenda_id, lote_id, nome, peso_kg),
        )
    return lote_id


def test_nome_vazio_e_latitude_invalida() -> None:
    with pytest.raises(ValidationError):
        ModuloIn(nome="")
    with pytest.raises(ValidationError):
        PracaIn(nome="Praça", lat=91, lon=0)
    with pytest.raises(ValidationError):
        PracaIn(nome="Praça", lat=0, lon=181)


def test_exemplo_trabalhado_lotacao(db_conn: psycopg.Connection[Any]) -> None:
    fid = _fazenda(db_conn)
    p1 = _piquete(db_conn, fid, "P1", 10.0)
    p2 = _piquete(db_conn, fid, "P2", 5.0)
    _piquete(db_conn, fid, "P3 desativado", 7.0, ativo=False)
    engorda = _lote(db_conn, fid, "Engorda", 16200.0)

    modulo = criar_modulo(db_conn, fid, ModuloIn(nome="Módulo A"))
    for pid in (p1, p2):
        definir_estrutura_piquete(db_conn, fid, pid, EstruturaPiqueteIn(modulo_id=modulo.id))
    definir_modulo_lote(db_conn, fid, engorda, LoteModuloIn(modulo_id=modulo.id))

    (lido,) = listar_modulos(db_conn, fid)
    assert lido.piquete_ids == [p1, p2]
    assert lido.lote_ids == [engorda]
    assert lido.area_ha == 15.0
    assert lido.ua_total == 36.0
    assert lido.lotacao_ua_ha == 2.4

    with pytest.raises(EmUsoError):
        excluir_modulo(db_conn, fid, modulo.id)


def test_modulo_sem_piquetes_tem_lotacao_none(db_conn: psycopg.Connection[Any]) -> None:
    fid = _fazenda(db_conn)
    modulo = criar_modulo(db_conn, fid, ModuloIn(nome="Vazio"))
    assert (modulo.area_ha, modulo.ua_total, modulo.lotacao_ua_ha) == (0.0, 0.0, None)
    excluir_modulo(db_conn, fid, modulo.id)
    assert listar_modulos(db_conn, fid) == []


def test_nome_duplicado_e_renomear(db_conn: psycopg.Connection[Any]) -> None:
    fid = _fazenda(db_conn)
    a = criar_modulo(db_conn, fid, ModuloIn(nome="A"))
    b = criar_modulo(db_conn, fid, ModuloIn(nome="B"))
    with pytest.raises(ValueError, match="Já existe um módulo"):
        criar_modulo(db_conn, fid, ModuloIn(nome="A"))
    with pytest.raises(ValueError, match="Já existe um módulo"):
        renomear_modulo(db_conn, fid, b.id, ModuloIn(nome="A"))
    assert renomear_modulo(db_conn, fid, a.id, ModuloIn(nome="A")).nome == "A"
    with pytest.raises(ValueError):
        criar_modulo(db_conn, fid, ModuloIn(nome="   "))
    with pytest.raises(LookupError, match="Módulo não encontrado"):
        renomear_modulo(db_conn, fid, uuid4(), ModuloIn(nome="C"))


def test_praca_ponto_e_em_uso(db_conn: psycopg.Connection[Any]) -> None:
    fid = _fazenda(db_conn)
    piquete = _piquete(db_conn, fid, "P1", 10.0)
    praca = criar_praca(db_conn, fid, PracaIn(nome="Praça 1", lat=-9.6, lon=-36.0))
    assert (praca.lat, praca.lon) == pytest.approx((-9.6, -36.0))

    editada = editar_praca(db_conn, fid, praca.id, PracaIn(nome="Praça 1", lat=-9.7, lon=-36.1))
    assert (editada.lat, editada.lon) == pytest.approx((-9.7, -36.1))
    assert listar_pracas(db_conn, fid) == [editada]

    definir_estrutura_piquete(db_conn, fid, piquete, EstruturaPiqueteIn(praca_id=praca.id))
    with pytest.raises(EmUsoError, match="Praça em uso"):
        excluir_praca(db_conn, fid, praca.id)
    definir_estrutura_piquete(db_conn, fid, piquete, EstruturaPiqueteIn())
    excluir_praca(db_conn, fid, praca.id)
    assert listar_pracas(db_conn, fid) == []


def test_isolamento_entre_fazendas(db_conn: psycopg.Connection[Any]) -> None:
    fid_a = _fazenda(db_conn, "Fazenda A")
    fid_b = _fazenda(db_conn, "Fazenda B")
    piquete_a = _piquete(db_conn, fid_a, "P1", 10.0)
    lote_a = _lote(db_conn, fid_a, "L1", 450.0)
    modulo_b = criar_modulo(db_conn, fid_b, ModuloIn(nome="B"))
    praca_b = criar_praca(db_conn, fid_b, PracaIn(nome="B", lat=0, lon=0))

    with pytest.raises(ValueError, match="Módulo de outra fazenda"):
        definir_estrutura_piquete(
            db_conn, fid_a, piquete_a, EstruturaPiqueteIn(modulo_id=modulo_b.id)
        )
    with pytest.raises(ValueError, match="Praça de outra fazenda"):
        definir_estrutura_piquete(
            db_conn, fid_a, piquete_a, EstruturaPiqueteIn(praca_id=praca_b.id)
        )
    with pytest.raises(ValueError, match="Módulo de outra fazenda"):
        definir_modulo_lote(db_conn, fid_a, lote_a, LoteModuloIn(modulo_id=modulo_b.id))
    with pytest.raises(LookupError, match="Piquete não encontrado"):
        definir_estrutura_piquete(db_conn, fid_b, piquete_a, EstruturaPiqueteIn())
    with pytest.raises(LookupError, match="Lote não encontrado"):
        definir_modulo_lote(db_conn, fid_b, lote_a, LoteModuloIn())
    with pytest.raises(LookupError, match="Módulo não encontrado"):
        excluir_modulo(db_conn, fid_a, modulo_b.id)
    assert listar_modulos(db_conn, fid_a) == []
    assert listar_pracas(db_conn, fid_a) == []


def test_obter_estrutura_e_limpar_vinculo(db_conn: psycopg.Connection[Any]) -> None:
    fid = _fazenda(db_conn)
    p1 = _piquete(db_conn, fid, "P1", 10.0)
    p2 = _piquete(db_conn, fid, "P2", 5.0)
    lote = _lote(db_conn, fid, "L1", 450.0)
    modulo = criar_modulo(db_conn, fid, ModuloIn(nome="A"))

    saida = definir_estrutura_piquete(db_conn, fid, p1, EstruturaPiqueteIn(modulo_id=modulo.id))
    assert (saida.piquete_id, saida.modulo_id, saida.praca_id) == (p1, modulo.id, None)
    definir_modulo_lote(db_conn, fid, lote, LoteModuloIn(modulo_id=modulo.id))

    estrutura = obter_estrutura(db_conn, fid)
    assert [(p.piquete_id, p.modulo_id) for p in estrutura.piquetes] == [
        (p1, modulo.id),
        (p2, None),
    ]
    assert [(lt.lote_id, lt.modulo_id) for lt in estrutura.lotes] == [(lote, modulo.id)]

    definir_estrutura_piquete(db_conn, fid, p1, EstruturaPiqueteIn())
    definir_modulo_lote(db_conn, fid, lote, LoteModuloIn())
    estrutura = obter_estrutura(db_conn, fid)
    assert all(p.modulo_id is None and p.praca_id is None for p in estrutura.piquetes)
    assert [lt.modulo_id for lt in estrutura.lotes] == [None]


def test_nada_e_escrito_em_evento(db_conn: psycopg.Connection[Any]) -> None:
    fid = _fazenda(db_conn)
    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM evento WHERE fazenda_id = %s", (fid,))
        antes = cur.fetchone()
    piquete = _piquete(db_conn, fid, "P1", 10.0)
    modulo = criar_modulo(db_conn, fid, ModuloIn(nome="A"))
    definir_estrutura_piquete(db_conn, fid, piquete, EstruturaPiqueteIn(modulo_id=modulo.id))
    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM evento WHERE fazenda_id = %s", (fid,))
        assert cur.fetchone() == antes
