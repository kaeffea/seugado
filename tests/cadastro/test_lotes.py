"""Test lotes."""

import uuid
from datetime import UTC, date, datetime

import pytest

from seugado.cadastro.clientes import ClienteIn, criar_cliente
from seugado.cadastro.fazenda import FazendaIn, criar_fazenda
from seugado.cadastro.lotes import (
    ComposicaoItemIn,
    LoteIn,
    criar_lote,
    dissolver_lote,
    editar_lote,
    listar_lotes,
)
from seugado.core.models import CategoriaAnimal, OrigemEvento, TipoEvento
from seugado.persistencia.eventos import registrar_evento
from seugado.persistencia.projecao_db import reconstruir_projecao


@pytest.fixture
def fazenda_para_lotes(db_conn):
    """Cria uma fazenda e piquetes para teste."""
    # Cria cliente e fazenda
    c_id = criar_cliente(db_conn, ClienteIn(nome="Cliente Lotes")).id
    f_id = criar_fazenda(
        db_conn,
        FazendaIn(
            cliente_id=c_id,
            nome="Fazenda Lotes",
            funcionarios_disponiveis=1,
            animais_por_funcionario_dia=100,
            dias_preferenciais_manejo=[0],
            envio_plano_dia=0,
            envio_plano_hora=8,
        )
    )
    
    # Cria piquete 1
    p1_id = uuid.uuid4()
    registrar_evento(
        conn=db_conn,
        fazenda_id=f_id,
        tipo=TipoEvento.PIQUETE_CRIADO,
        origem=OrigemEvento.PRODUTOR,
        ocorrido_em=datetime.now(UTC),
        payload={
            "entidade_id": str(p1_id),
            "nome": "Piquete 1",
            "area_ha": 10.0,
            "cultivar_id": str(uuid.uuid4()),  # Doesn't matter
            "metodo_pastejo": "continuo",
            "ativo": True,
            "geometria_geojson": {
                "type": "Polygon",
                "coordinates": [[[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]]
            },
        },
        ator="tester"
    )
    
    # Cria piquete 2
    p2_id = uuid.uuid4()
    registrar_evento(
        conn=db_conn,
        fazenda_id=f_id,
        tipo=TipoEvento.PIQUETE_CRIADO,
        origem=OrigemEvento.PRODUTOR,
        ocorrido_em=datetime.now(UTC),
        payload={
            "entidade_id": str(p2_id),
            "nome": "Piquete 2",
            "area_ha": 10.0,
            "cultivar_id": str(uuid.uuid4()),
            "metodo_pastejo": "continuo",
            "ativo": True,
            "geometria_geojson": {
                "type": "Polygon",
                "coordinates": [[[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]]
            },
        },
        ator="tester"
    )
    
    reconstruir_projecao(db_conn, f_id)
    return f_id, p1_id, p2_id


def test_lotes_lifecycle(db_conn, fazenda_para_lotes):
    """Test creating, editing, and dissolving a lote."""
    f_id, p1_id, p2_id = fazenda_para_lotes
    
    # 1. Create lote
    dados = LoteIn(
        nome="Lote 1",
        indissoluvel=False,
        composicao=[
            ComposicaoItemIn(categoria=CategoriaAnimal.NOVILHO, n_animais=50)
        ],
        piquete_atual_id=p1_id,
        desde=date(2026, 9, 20)
    )
    
    lote_id = criar_lote(db_conn, f_id, "tester", dados)
    
    # List lotes
    lotes = listar_lotes(db_conn, f_id)
    assert len(lotes) == 1
    lote = lotes[0]
    assert lote.id == lote_id
    assert lote.nome == "Lote 1"
    assert lote.piquete_atual_id == p1_id
    assert lote.desde == date(2026, 9, 20)
    assert len(lote.composicao) == 1
    assert lote.composicao[0].peso_medio_kg == 337.5  # default value from ua_tabela
    
    # 2. Edit lote (change piquete and name)
    dados_edit = LoteIn(
        nome="Lote 1 Modificado",
        indissoluvel=True,
        composicao=[
            ComposicaoItemIn(categoria=CategoriaAnimal.NOVILHO, n_animais=60, peso_medio_kg=350.0)
        ],
        piquete_atual_id=p2_id
    )
    
    editar_lote(db_conn, f_id, lote_id, "tester", dados_edit)
    
    lotes = listar_lotes(db_conn, f_id)
    lote = lotes[0]
    assert lote.nome == "Lote 1 Modificado"
    assert lote.indissoluvel is True
    assert lote.piquete_atual_id == p2_id
    assert lote.composicao[0].n_animais == 60
    assert lote.composicao[0].peso_medio_kg == 350.0
    
    # 3. Dissolve lote
    dissolver_lote(db_conn, f_id, lote_id, "tester")
    lotes = listar_lotes(db_conn, f_id)
    assert len(lotes) == 0
