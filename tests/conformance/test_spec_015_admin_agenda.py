"""Independent conformance suite covering SPEC-015 (Admin, agenda e categorias).

Written by the tester role (Antigravity), not the implementer.
Tests map to requirements of SPEC-015 and verification scenarios in KIT-ACEITE-015.
"""

import os
import uuid
from dataclasses import fields, is_dataclass
from pathlib import Path
from unittest.mock import MagicMock

import psycopg
import pytest
from fastapi import HTTPException
from psycopg import errors
from pydantic import ValidationError

from seugado.api import auth
from seugado.contratos import DiferencaLote, PassoPlano, TipoAlerta
from seugado.core.models import CategoriaAnimal, ComposicaoLote, Fazenda, OrigemPeso
from seugado.persistencia import eventos
from seugado.planner import estado

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
MIGRATION_0003 = ROOT / "db" / "migrations" / "0003_admin_agenda.sql"


# ==============================================================================
# Structural Checks (KIT-ACEITE-015)
# ==============================================================================


def test_categoria_animal_seven_members_order_no_adulto():
    """CategoriaAnimal: 7 members in spec order; ADULTO does not exist."""
    expected_order = [
        "bezerro",
        "bezerra",
        "novilho",
        "novilha",
        "vaca",
        "boi",
        "touro",
    ]
    actual_values = [m.value for m in CategoriaAnimal]
    assert actual_values == expected_order
    assert len(CategoriaAnimal) == 7
    assert "ADULTO" not in CategoriaAnimal.__members__


def test_fazenda_fields_order_and_no_manejos_por_funcionario_dia_in_src():
    """Fazenda: exact field order; manejos_por_funcionario_dia does not exist anywhere in src/."""
    assert is_dataclass(Fazenda)
    params = getattr(Fazenda, "__dataclass_params__", None)
    assert params is not None and params.frozen is True
    assert hasattr(Fazenda, "__slots__")

    expected_fields = [
        "id",
        "nome",
        "timezone",
        "funcionarios_disponiveis",
        "animais_por_funcionario_dia",
        "dias_preferenciais_manejo",
        "envio_plano_dia",
        "envio_plano_hora",
        "ativo",
    ]
    actual_fields = [f.name for f in fields(Fazenda)]
    assert actual_fields == expected_fields

    # Verify manejos_por_funcionario_dia does not exist anywhere in src/
    for py_file in SRC_DIR.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "manejos_por_funcionario_dia" not in content, (
            f"Found 'manejos_por_funcionario_dia' in {py_file}"
        )


def test_tipo_alerta_and_new_contracts_frozen_slotted():
    """TipoAlerta with 9 members; PassoPlano and DiferencaLote frozen and slotted."""
    assert len(TipoAlerta) == 9
    assert TipoAlerta.PASSANDO_DO_PONTO.value == "passando_do_ponto"

    for cls in (PassoPlano, DiferencaLote):
        assert is_dataclass(cls), f"{cls.__name__} must be a dataclass"
        params = getattr(cls, "__dataclass_params__", None)
        assert params is not None and params.frozen is True, f"{cls.__name__} must be frozen"
        assert hasattr(cls, "__slots__"), f"{cls.__name__} must have slots"


def test_migration_0003_structure():
    """0003_admin_agenda.sql is wrapped in BEGIN...COMMIT and contains all schema modifications."""
    content = MIGRATION_0003.read_text(encoding="utf-8").strip()
    assert content.startswith("BEGIN;")
    assert content.endswith("COMMIT;")
    assert "CREATE TABLE cliente" in content
    assert "ALTER TABLE cliente ENABLE ROW LEVEL SECURITY" in content
    assert "ALTER TABLE fazenda ADD COLUMN cliente_id" in content
    assert (
        "ALTER TABLE fazenda RENAME COLUMN manejos_por_funcionario_dia TO"
        " animais_por_funcionario_dia"
        in content
    )
    assert "envio_plano_dia" in content
    assert "envio_plano_hora" in content
    assert "ultimo_envio_semanal" in content
    assert "fazenda_telegram_chat_idx" in content
    assert "ALTER TABLE plano ADD COLUMN status" in content


def test_migration_0003_applied_in_database():
    """0003 applied: cliente exists with RLS; fazenda has new columns; plano.status with CHECK."""
    db_url = os.environ.get("SEUGADO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        pytest.skip("No database URL set; skipping live DB schema check")

    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        # 1. cliente exists and has RLS enabled
        cur.execute("""
            SELECT relrowsecurity 
            FROM pg_class 
            JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
            WHERE pg_namespace.nspname = 'public' AND pg_class.relname = 'cliente';
        """)
        row = cur.fetchone()
        assert row is not None, "Table 'cliente' does not exist"
        assert row[0] is True, "Table 'cliente' does not have RLS enabled"

        # 2. fazenda columns
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'fazenda';
        """)
        fazenda_cols = {r[0] for r in cur.fetchall()}
        assert "cliente_id" in fazenda_cols
        assert "animais_por_funcionario_dia" in fazenda_cols
        assert "envio_plano_dia" in fazenda_cols
        assert "envio_plano_hora" in fazenda_cols
        assert "ultimo_envio_semanal" in fazenda_cols
        assert "manejos_por_funcionario_dia" not in fazenda_cols

        # 3. plano status column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'plano';
        """)
        plano_cols = {r[0] for r in cur.fetchall()}
        assert "status" in plano_cols


# ==============================================================================
# Canonical Case (KIT-ACEITE-015)
# ==============================================================================


def test_canonical_case_30_touros_sem_peso():
    """30 touros sem peso -> 562,5 kg e 405,0 kg MS/dia."""
    # Fallback weight: 1.25 * 450 = 562.5 kg
    peso_fallback = estado.peso_por_ua_kg(CategoriaAnimal.TOURO)
    assert peso_fallback == pytest.approx(562.5)

    # Intake: 30 * 562.5 * 0.024 = 405.0 kg MS/day
    comp = (ComposicaoLote(CategoriaAnimal.TOURO, 30, peso_fallback, OrigemPeso.UA_TABELA),)
    consumo = estado.consumo_lote(comp)
    assert consumo == pytest.approx(405.0)


# ==============================================================================
# Hidden Cases (KIT-ACEITE-015)
# ==============================================================================


def test_hidden_case_1_composicao_payload_adulto_raises_validation_error():
    """Caso 1: ComposicaoPayload(categoria="adulto", ...) -> ValidationError."""
    with pytest.raises(ValidationError):
        eventos.ComposicaoPayload(
            categoria="adulto",  # type: ignore[arg-type]
            n_animais=10,
            peso_medio_kg=450.0,
            origem_peso="produtor",
        )


def test_hidden_case_2_exigir_fazenda_404_and_returns_id():
    """Caso 2: exigir_fazenda com UUID inexistente -> 404; com existente -> devolve id."""
    usuario = auth.UsuarioAtual(id=uuid.uuid4(), email="admin@seugado.com")

    # With mock
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    # Nonexistent
    mock_cur.fetchone.return_value = None
    inexistente_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        auth.exigir_fazenda(inexistente_id, usuario, mock_conn)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Fazenda não encontrada"

    # Existing farm
    mock_cur.fetchone.return_value = (1,)
    existente_id = uuid.uuid4()
    ret = auth.exigir_fazenda(existente_id, usuario, mock_conn)
    assert ret == existente_id


def test_hidden_case_3_telegram_chat_id_unique_index():
    """Caso 3: Dois UPDATE fazenda com mesmo telegram_chat_id viola índice único."""
    db_url = os.environ.get("SEUGADO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        pytest.skip("No database URL set; skipping live DB unique index test")

    f1_id = uuid.uuid4()
    f2_id = uuid.uuid4()
    chat_id = 999999999

    with psycopg.connect(db_url) as conn:
        try:
            with conn.cursor() as cur:
                insert_sql = (
                    "INSERT INTO fazenda (id, nome, timezone, funcionarios_disponiveis,"
                    " animais_por_funcionario_dia) VALUES (%s, %s, 'America/Maceio', 1, 100)"
                )
                cur.execute(insert_sql, (f1_id, "F1"))
                cur.execute(insert_sql, (f2_id, "F2"))

                # Set chat_id on f1
                cur.execute(
                    "UPDATE fazenda SET telegram_chat_id = %s WHERE id = %s",
                    (chat_id, f1_id),
                )

                # Setting same chat_id on f2 must raise UniqueViolation
                with pytest.raises(errors.UniqueViolation):
                    cur.execute(
                        "UPDATE fazenda SET telegram_chat_id = %s WHERE id = %s",
                        (chat_id, f2_id),
                    )
        finally:
            conn.rollback()


def test_hidden_case_4_consumo_lote_novilha():
    """Caso 4: consumo_lote com 10 novilha de 337,5 kg -> 74,25."""
    assert estado.peso_por_ua_kg(CategoriaAnimal.NOVILHA) == pytest.approx(337.5)
    comp = (ComposicaoLote(CategoriaAnimal.NOVILHA, 10, 337.5, OrigemPeso.PRODUTOR),)
    # 10 * 337.5 * 0.022 = 74.25
    consumo = estado.consumo_lote(comp)
    assert consumo == pytest.approx(74.25)
