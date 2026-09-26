"""Independent conformance suite covering SPEC-008 (Banco MVP).

Written by the tester role (Antigravity), not the implementer.
Tests map to requirements of SPEC-008 and verification scenarios in KIT-ACEITE-008.
"""

import ast
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from seugado.core.models import (
    Confianca,
    MetodoPastejo,
    OrigemEvento,
    TipoEvento,
)
from seugado.persistencia import catalogo, eventos, projecao_db

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_0001 = ROOT / "db" / "migrations" / "0001_evento_e_derivadas.sql"
MIGRATION_0002 = ROOT / "db" / "migrations" / "0002_mvp.sql"

EXPECTED_SLUGS = {
    "marandu",
    "mombaca",
    "tanzania",
    "zuri",
    "massai",
    "tamani",
    "xaraes",
    "piata",
    "decumbens",
}


# ==============================================================================
# Structural Checks (KIT-ACEITE-008)
# ==============================================================================


def test_migration_0002_wrapped_in_transaction():
    """0002_mvp.sql is wrapped in BEGIN; ... COMMIT; and 0001 is unmodified."""
    content_0002 = MIGRATION_0002.read_text(encoding="utf-8").strip()
    assert "BEGIN;" in content_0002
    assert "COMMIT;" in content_0002
    assert content_0002.endswith("COMMIT;")

    # 0001 file exists and does not contain 0002 tables like cultivar or fazenda_usuario
    content_0001 = MIGRATION_0001.read_text(encoding="utf-8")
    assert "fazenda_usuario" not in content_0001
    assert "cultivar" not in content_0001


def test_no_commit_or_rollback_in_projecao_db_and_catalogo():
    """reconstruir_projecao and carregar_catalogo must not call commit() or rollback()."""
    for py_file in (
        ROOT / "src" / "seugado" / "persistencia" / "projecao_db.py",
        ROOT / "src" / "seugado" / "persistencia" / "catalogo.py",
    ):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in ("commit", "rollback"), (
                    f"{py_file.name} calls forbidden {node.func.attr}() on line {node.lineno}"
                )


def test_no_fstring_in_sql_execution():
    """No f-strings are used to construct SQL statements with data."""
    for py_file in (
        ROOT / "src" / "seugado" / "persistencia" / "projecao_db.py",
        ROOT / "src" / "seugado" / "persistencia" / "catalogo.py",
    ):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "execute"
                and node.args
            ):
                first_arg = node.args[0]
                assert not isinstance(first_arg, ast.JoinedStr), (
                    f"f-string SQL execution in {py_file.name} on line {node.lineno}"
                )


# ==============================================================================
# Database Structural Checks (require live DB)
# ==============================================================================


@pytest.fixture
def db_conn():
    url = os.environ.get("SEUGADO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("SEUGADO_TEST_DATABASE_URL not set; skipping live DB test")
    conn = psycopg.connect(url, autocommit=False)
    yield conn
    conn.rollback()
    conn.close()


def test_db_rls_and_policies(db_conn):
    """RLS enabled on all 12 tables and 0 public policies exist."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM pg_policies WHERE schemaname = 'public'")
        row = cur.fetchone()
        assert row is not None and row[0] == 0

        # Check RLS on key tables
        tables_to_check = [
            "fazenda",
            "fazenda_usuario",
            "cultivar",
            "evento",
            "tipo_evento",
            "origem_evento",
            "estado_piquete",
            "estado_lote",
            "leitura",
            "altura_atual",
            "plano",
            "telegram_conversa",
        ]
        for tbl in tables_to_check:
            cur.execute(
                "SELECT relrowsecurity FROM pg_class WHERE relname = %s",
                (tbl,),
            )
            res = cur.fetchone()
            assert res is not None and res[0] is True, f"RLS not enabled on table {tbl}"


def test_db_cultivar_count_and_slugs(db_conn):
    """SELECT count(*) FROM cultivar returns 9 with exact expected slugs."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT slug FROM cultivar")
        slugs = {row[0] for row in cur.fetchall()}
        assert len(slugs) == 9
        assert slugs == EXPECTED_SLUGS


# ==============================================================================
# Canonical Case (Worked Example in SPEC-008)
# ==============================================================================


def test_canonical_worked_example():
    """Worked example: Xaraes has only continuo block. Two overrides create rotacionado."""
    xaraes_json = {
        "especie": "Brachiaria brizantha",
        "via_fotossintetica": "C4",
        "por_regime": [
            {
                "metodo": "continuo",
                "altura_entrada_cm": None,
                "altura_saida_cm": None,
                "altura_maxima_cm": 40,
                "altura_minima_cm": 25,
                "confianca": "alta",
                "fonte": "CT-135",
            }
        ],
        "densidade_kg_ha_por_cm": None,
        "rue_max_g_por_mj": None,
        "temperatura_base_c": None,
        "descanso_min_dias": 21,
        "descanso_max_dias": 45,
        "qualidade_base": None,
    }
    xaraes_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()

    xaraes = catalogo.cultivar_de_linha(xaraes_id, "xaraes", "Xaraés", xaraes_json)
    assert len(xaraes.parametros_por_regime) == 1
    assert xaraes.parametros_por_regime[0].metodo == MetodoPastejo.CONTINUO

    # First override: altura_entrada_cm = 35
    overrides_1 = [(MetodoPastejo.ROTACIONADO, "altura_entrada_cm", 35.0)]
    xaraes_pos_1 = catalogo.aplicar_overrides(xaraes, overrides_1, fazenda_id)
    res_1 = catalogo.resolver_alturas(xaraes_pos_1, MetodoPastejo.ROTACIONADO)
    assert res_1.faltantes == ("altura_saida_cm",)

    # Second override: altura_saida_cm = 18
    overrides_2 = [
        (MetodoPastejo.ROTACIONADO, "altura_entrada_cm", 35.0),
        (MetodoPastejo.ROTACIONADO, "altura_saida_cm", 18.0),
    ]
    xaraes_pos_2 = catalogo.aplicar_overrides(xaraes, overrides_2, fazenda_id)
    assert len(xaraes_pos_2.parametros_por_regime) == 2

    # Untouched continuo block remains
    continuo_bloco = next(
        b for b in xaraes_pos_2.parametros_por_regime if b.metodo == MetodoPastejo.CONTINUO
    )
    assert continuo_bloco.altura_maxima_cm == 40.0
    assert continuo_bloco.confianca == Confianca.ALTA

    # Rotacionado block created with low confidence and producer source
    rot_bloco = next(
        b for b in xaraes_pos_2.parametros_por_regime if b.metodo == MetodoPastejo.ROTACIONADO
    )
    assert rot_bloco.altura_entrada_cm == 35.0
    assert rot_bloco.altura_saida_cm == 18.0
    assert rot_bloco.confianca == Confianca.BAIXA
    assert rot_bloco.fonte == f"produtor:{fazenda_id}"

    # Now resolver_alturas has no faltantes
    res_2 = catalogo.resolver_alturas(xaraes_pos_2, MetodoPastejo.ROTACIONADO)
    assert res_2.faltantes == ()
    assert res_2.parametros is not None
    assert res_2.parametros.altura_entrada_cm == 35.0


# ==============================================================================
# Casos que a spec não mostra (KIT-ACEITE-008)
# ==============================================================================


def test_hidden_case_1_override_preserves_unmodified_field():
    """Caso 1: aplicar_overrides no Marandu modifica entrada 28, preserva saida 15."""
    marandu_json = {
        "especie": "Brachiaria brizantha",
        "via_fotossintetica": "C4",
        "por_regime": [
            {
                "metodo": "rotacionado",
                "altura_entrada_cm": 30,
                "altura_saida_cm": 15,
                "altura_maxima_cm": None,
                "altura_minima_cm": None,
                "eficiencia_pastejo": 0.72,
                "confianca": "media",
                "fonte": "Andrade",
            },
            {
                "metodo": "continuo",
                "altura_entrada_cm": None,
                "altura_saida_cm": None,
                "altura_maxima_cm": 35,
                "altura_minima_cm": 20,
                "confianca": "alta",
                "fonte": "CT-135",
            },
        ],
        "densidade_kg_ha_por_cm": 110,
        "rue_max_g_por_mj": 2.31,
        "temperatura_base_c": 15.0,
        "descanso_min_dias": 21,
        "descanso_max_dias": 45,
        "qualidade_base": "alta",
    }
    faz_id = uuid.uuid4()
    marandu = catalogo.cultivar_de_linha(uuid.uuid4(), "marandu", "Marandu", marandu_json)

    overrides = [(MetodoPastejo.ROTACIONADO, "altura_entrada_cm", 28.0)]
    modificado = catalogo.aplicar_overrides(marandu, overrides, faz_id)

    rot = next(b for b in modificado.parametros_por_regime if b.metodo == MetodoPastejo.ROTACIONADO)
    assert rot.altura_entrada_cm == 28.0
    assert rot.altura_saida_cm == 15.0  # preserved!
    assert rot.confianca == Confianca.BAIXA
    assert rot.fonte == f"produtor:{faz_id}"

    cont = next(b for b in modificado.parametros_por_regime if b.metodo == MetodoPastejo.CONTINUO)
    assert cont.altura_maxima_cm == 35.0  # intact!
    assert cont.confianca == Confianca.ALTA


def test_hidden_case_2_faltantes_calibracao_marandu():
    """Caso 2: Marandu is fully calibrated in both continuo and rotacionado."""
    marandu_json = {
        "especie": "Brachiaria brizantha",
        "via_fotossintetica": "C4",
        "por_regime": [
            {
                "metodo": "rotacionado",
                "altura_entrada_cm": 30,
                "altura_saida_cm": 15,
                "altura_maxima_cm": None,
                "altura_minima_cm": None,
                "eficiencia_pastejo": 0.72,
                "confianca": "media",
                "fonte": "Andrade",
            },
            {
                "metodo": "continuo",
                "altura_entrada_cm": None,
                "altura_saida_cm": None,
                "altura_maxima_cm": 35,
                "altura_minima_cm": 20,
                "confianca": "alta",
                "fonte": "CT-135",
            },
        ],
        "densidade_kg_ha_por_cm": 110,
        "rue_max_g_por_mj": 2.31,
        "temperatura_base_c": 15.0,
        "descanso_min_dias": 21,
        "descanso_max_dias": 45,
        "qualidade_base": "alta",
    }
    marandu = catalogo.cultivar_de_linha(uuid.uuid4(), "marandu", "Marandu", marandu_json)
    assert catalogo.faltantes_calibracao(marandu, MetodoPastejo.CONTINUO) == ()
    assert catalogo.faltantes_calibracao(marandu, MetodoPastejo.ROTACIONADO) == ()


def test_hidden_case_3_faltantes_calibracao_piata():
    """Caso 3: Piata missing densidade in continuo."""
    piata_json = {
        "especie": "Brachiaria brizantha",
        "via_fotossintetica": "C4",
        "por_regime": [
            {
                "metodo": "continuo",
                "altura_entrada_cm": None,
                "altura_saida_cm": None,
                "altura_maxima_cm": 45,
                "altura_minima_cm": 30,
                "confianca": "alta",
                "fonte": "CT-135",
            }
        ],
        "densidade_kg_ha_por_cm": None,
        "rue_max_g_por_mj": 2.31,
        "temperatura_base_c": 15.0,
        "descanso_min_dias": 21,
        "descanso_max_dias": 45,
        "qualidade_base": "alta",
    }
    piata = catalogo.cultivar_de_linha(uuid.uuid4(), "piata", "Piatã", piata_json)
    assert catalogo.faltantes_calibracao(piata, MetodoPastejo.CONTINUO) == (
        "densidade_kg_ha_por_cm",
    )


def test_hidden_case_4_reconstruir_idempotente_postgis_geometria(db_conn):
    """Caso 4: criar fazenda + 1 piquete, reconstruir_projecao 2x.

    Verifica que ha 1 linha em estado_piquete e ST_IsValid e verdadeiro.
    """
    fazenda_id = uuid.uuid4()
    piquete_id = uuid.uuid4()
    cultivar_id = uuid.uuid4()

    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO fazenda (id, nome) VALUES (%s, %s)",
            (fazenda_id, "Fazenda Teste PostGIS"),
        )

    square_geojson = {
        "type": "Polygon",
        "coordinates": [
            [[-36.10, -9.80], [-36.10, -9.79], [-36.09, -9.79], [-36.09, -9.80], [-36.10, -9.80]]
        ],
    }

    eventos.registrar_evento(
        db_conn,
        fazenda_id,
        TipoEvento.PIQUETE_CRIADO,
        OrigemEvento.PRODUTOR,
        datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
        {
            "entidade_id": piquete_id,
            "nome": "Piquete PostGIS",
            "area_ha": 10.0,
            "cultivar_id": cultivar_id,
            "metodo_pastejo": "rotacionado",
            "ativo": True,
            "geometria_geojson": square_geojson,
        },
    )

    # First projection
    projecao_db.reconstruir_projecao(db_conn, fazenda_id)
    # Second projection (idempotency check)
    projecao_db.reconstruir_projecao(db_conn, fazenda_id)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*), ST_IsValid(geometria), ST_GeometryType(geometria) "
            "FROM estado_piquete WHERE fazenda_id = %s GROUP BY geometria",
            (fazenda_id,),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == 1, "Expected exactly 1 row in estado_piquete"
        assert row[1] is True, "Expected valid PostGIS geometry"
        assert row[2] == "ST_Polygon", "Expected ST_Polygon geometry type"
