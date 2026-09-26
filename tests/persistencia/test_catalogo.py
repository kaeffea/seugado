import os
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest

from seugado.core.models import (
    Confianca,
    Evento,
    MetodoPastejo,
    OrigemEvento,
    QualidadeBase,
    TipoEvento,
)
from seugado.persistencia.catalogo import (
    aplicar_overrides,
    carregar_catalogo,
    cultivar_de_linha,
    eficiencia_pastejo,
    faltantes_calibracao,
    overrides_da_fazenda,
    resolver_alturas,
)

precisa_banco = pytest.mark.skipif(
    not os.environ.get("SEUGADO_TEST_DATABASE_URL"), reason="needs SEUGADO_TEST_DATABASE_URL"
)

FAZENDA_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CULTIVAR_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _marandu() -> dict[str, Any]:
    return {
        "por_regime": [
            {
                "metodo": "rotacionado",
                "altura_entrada_cm": 30,
                "altura_saida_cm": 15,
                "altura_maxima_cm": None,
                "altura_minima_cm": None,
                "eficiencia_pastejo": 0.72,
                "confianca": "media",
                "fonte": "seed",
            },
            {
                "metodo": "continuo",
                "altura_entrada_cm": None,
                "altura_saida_cm": None,
                "altura_maxima_cm": 35,
                "altura_minima_cm": 20,
                "confianca": "alta",
                "fonte": "seed",
            },
        ],
        "densidade_kg_ha_por_cm": 110,
        "rue_max_g_por_mj": 2.31,
        "temperatura_base_c": 15.0,
        "descanso_min_dias": 21,
        "qualidade_base": "alta",
    }


def _xaraes() -> dict[str, Any]:
    return {
        "por_regime": [
            {
                "metodo": "continuo",
                "altura_entrada_cm": None,
                "altura_saida_cm": None,
                "altura_maxima_cm": 40,
                "altura_minima_cm": 20,
                "confianca": "alta",
                "fonte": "seed",
            }
        ],
        "densidade_kg_ha_por_cm": None,
        "rue_max_g_por_mj": None,
        "temperatura_base_c": None,
        "descanso_min_dias": 21,
        "qualidade_base": None,
    }


def _evento_override(
    dia: int, sequencia: int, campo: str, valor: float, cultivar_id: uuid.UUID = CULTIVAR_ID
) -> Evento:
    return Evento(
        id=uuid.uuid4(),
        fazenda_id=FAZENDA_ID,
        tipo=TipoEvento.PARAMETRO_ALTERADO,
        ocorrido_em=datetime(2026, 9, dia, 9, 0, tzinfo=UTC),
        registrado_em=datetime(2026, 9, dia, 9, 5, tzinfo=UTC),
        payload={
            "entidade_id": str(uuid.uuid4()),
            "cultivar_id": str(cultivar_id),
            "metodo_pastejo": "rotacionado",
            "campo": campo,
            "valor": valor,
            "origem": "produtor",
            "confianca": "baixa",
        },
        origem=OrigemEvento.PRODUTOR,
        sequencia=sequencia,
    )


def test_cultivar_de_linha_interpreta_regimes():
    c = cultivar_de_linha(CULTIVAR_ID, "marandu", "Marandu", _marandu())
    assert [b.metodo for b in c.parametros_por_regime] == [
        MetodoPastejo.ROTACIONADO,
        MetodoPastejo.CONTINUO,
    ]
    assert c.parametros_por_regime[0].altura_entrada_cm == 30
    assert c.eficiencia_por_metodo == ((MetodoPastejo.ROTACIONADO, 0.72),)
    assert c.densidade_kg_ha_por_cm == 110
    assert c.qualidade_base == QualidadeBase.ALTA
    assert c.descanso_min_dias == 21


def test_cultivar_de_linha_rejeita_forma_invalida():
    with pytest.raises(ValueError):
        cultivar_de_linha(CULTIVAR_ID, "x", "X", {"densidade_kg_ha_por_cm": 1})
    ruim_metodo = _xaraes()
    ruim_metodo["por_regime"][0]["metodo"] = "diario"
    with pytest.raises(ValueError):
        cultivar_de_linha(CULTIVAR_ID, "x", "X", ruim_metodo)
    ruim_confianca = _xaraes()
    ruim_confianca["por_regime"][0]["confianca"] = "total"
    with pytest.raises(ValueError):
        cultivar_de_linha(CULTIVAR_ID, "x", "X", ruim_confianca)


def test_overrides_da_fazenda_mantem_ultimo_valor():
    outro = _evento_override(3, 3, "altura_saida_cm", 18.0)
    eventos = [
        _evento_override(1, 1, "altura_entrada_cm", 30.0),
        _evento_override(2, 2, "altura_entrada_cm", 35.0),
        outro,
    ]
    eventos.append(replace(eventos[0], id=uuid.uuid4(), tipo=TipoEvento.FOTO_VALIDACAO))
    overrides = overrides_da_fazenda(eventos)
    assert overrides[CULTIVAR_ID] == (
        (MetodoPastejo.ROTACIONADO, "altura_entrada_cm", 35.0),
        (MetodoPastejo.ROTACIONADO, "altura_saida_cm", 18.0),
    )


def test_aplicar_overrides_cria_bloco_com_fonte_do_produtor():
    xaraes = cultivar_de_linha(CULTIVAR_ID, "xaraes", "Xaraés", _xaraes())
    com_um = aplicar_overrides(
        xaraes, [(MetodoPastejo.ROTACIONADO, "altura_entrada_cm", 35.0)], FAZENDA_ID
    )
    assert resolver_alturas(com_um, MetodoPastejo.ROTACIONADO).faltantes == ("altura_saida_cm",)
    com_dois = aplicar_overrides(
        xaraes,
        [
            (MetodoPastejo.ROTACIONADO, "altura_entrada_cm", 35.0),
            (MetodoPastejo.ROTACIONADO, "altura_saida_cm", 18.0),
        ],
        FAZENDA_ID,
    )
    assert resolver_alturas(com_dois, MetodoPastejo.ROTACIONADO).faltantes == ()
    rot = [b for b in com_dois.parametros_por_regime if b.metodo == MetodoPastejo.ROTACIONADO][0]
    assert (rot.altura_entrada_cm, rot.altura_saida_cm) == (35.0, 18.0)
    assert rot.confianca == Confianca.BAIXA
    assert rot.fonte == f"produtor:{FAZENDA_ID}"
    cont = [b for b in com_dois.parametros_por_regime if b.metodo == MetodoPastejo.CONTINUO][0]
    assert cont.confianca == Confianca.ALTA  # untouched block kept


def test_aplicar_overrides_rejeita_campo():
    xaraes = cultivar_de_linha(CULTIVAR_ID, "xaraes", "Xaraés", _xaraes())
    with pytest.raises(ValueError):
        aplicar_overrides(xaraes, [(MetodoPastejo.CONTINUO, "rue_max", 1.0)], FAZENDA_ID)


def test_eficiencia_e_faltantes():
    marandu = cultivar_de_linha(CULTIVAR_ID, "marandu", "Marandu", _marandu())
    assert eficiencia_pastejo(marandu, MetodoPastejo.ROTACIONADO) == 0.72
    assert eficiencia_pastejo(marandu, MetodoPastejo.CONTINUO) is None
    assert faltantes_calibracao(marandu, MetodoPastejo.ROTACIONADO) == ()
    mombaca = cultivar_de_linha(
        CULTIVAR_ID,
        "mombaca",
        "Mombaça",
        {**_xaraes(), "qualidade_base": "alta"},
    )
    assert faltantes_calibracao(mombaca, MetodoPastejo.ROTACIONADO) == (
        "densidade_kg_ha_por_cm",
        "rue_max_g_por_mj",
        "eficiencia_pastejo",
    )
    assert faltantes_calibracao(mombaca, MetodoPastejo.CONTINUO) == (
        "densidade_kg_ha_por_cm",
        "rue_max_g_por_mj",
    )


@precisa_banco
def test_carregar_catalogo_sem_fazenda():
    import psycopg

    conn = psycopg.connect(os.environ["SEUGADO_TEST_DATABASE_URL"])
    try:
        catalogo = carregar_catalogo(conn, None)
        assert len(catalogo) == 9
        marandu = next(c for c in catalogo.values() if c.slug == "marandu")
        assert marandu.densidade_kg_ha_por_cm == 110
    finally:
        conn.rollback()
        conn.close()


@precisa_banco
def test_carregar_catalogo_aplica_overrides_da_fazenda():
    import psycopg

    from seugado.persistencia.eventos import registrar_evento

    conn = psycopg.connect(os.environ["SEUGADO_TEST_DATABASE_URL"])
    try:
        fazenda_id = uuid.uuid4()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO fazenda (id) VALUES (%s)", (fazenda_id,))
            cur.execute("SELECT id FROM cultivar WHERE slug = %s", ("xaraes",))
            row = cur.fetchone()
            assert row is not None
            xaraes_id = row[0]
        for dia, campo, valor in ((1, "altura_entrada_cm", 35.0), (2, "altura_saida_cm", 18.0)):
            registrar_evento(
                conn,
                fazenda_id,
                TipoEvento.PARAMETRO_ALTERADO,
                OrigemEvento.PRODUTOR,
                datetime(2026, 9, dia, 9, 0, tzinfo=UTC),
                {
                    "entidade_id": uuid.uuid4(),
                    "cultivar_id": xaraes_id,
                    "metodo_pastejo": "rotacionado",
                    "campo": campo,
                    "valor": valor,
                    "origem": "produtor",
                    "confianca": "baixa",
                },
            )
        xaraes = carregar_catalogo(conn, fazenda_id)[xaraes_id]
        rot = [b for b in xaraes.parametros_por_regime if b.metodo == MetodoPastejo.ROTACIONADO][0]
        assert (rot.altura_entrada_cm, rot.altura_saida_cm) == (35.0, 18.0)
        assert rot.fonte == f"produtor:{fazenda_id}"
    finally:
        conn.rollback()
        conn.close()
