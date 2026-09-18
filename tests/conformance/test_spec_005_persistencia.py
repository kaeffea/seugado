"""Independent conformance suite covering SPEC-005 (persistencia/eventos.py and migrations).

Written by the tester role, not the implementer. Tests map to requirements
and acceptance criteria of SPEC-005 and verification scenarios in KIT-ACEITE-005.
"""

import ast
import inspect
import os
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from seugado.core.models import OrigemEvento, TipoEvento
from seugado.persistencia import eventos

ROOT = Path(__file__).resolve().parents[2]
EVENTOS_PATH = ROOT / "src" / "seugado" / "persistencia" / "eventos.py"
SOURCE = EVENTOS_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

MIGRATION_PATH = ROOT / "db" / "migrations" / "0001_evento_e_derivadas.sql"

ALLOWED_MODULES = {
    "datetime",
    "typing",
    "uuid",
    "psycopg",
    "pydantic",
    "seugado.core.models",
}


# ==============================================================================
# Structural Checks (KIT-ACEITE-005)
# ==============================================================================


def test_migration_file_structure():
    """Verify the SQL migration creates exact expected tables and no drops."""
    assert MIGRATION_PATH.exists(), f"Migration file missing at {MIGRATION_PATH}"
    sql = MIGRATION_PATH.read_text(encoding="utf-8").lower()

    assert "drop " not in sql, "Migration contains forbidden DROP statement"

    expected_tables = [
        "tipo_evento",
        "origem_evento",
        "fazenda",
        "evento",
        "estado_piquete",
        "estado_lote",
        "leitura",
    ]
    for table in expected_tables:
        assert "create table" in sql and table in sql, f"Table {table} not created in migration"

    # Verbatim checks from ADR-018
    assert "revoke update, delete on evento from public" in sql
    assert "trg_impedir_alteracao_evento" in sql or "impedir_alteracao_evento" in sql
    assert "chave_idempotencia" in sql
    assert "entidade_id" in sql and "generated always as" in sql


def test_imports_whitelist_in_eventos():
    """Verify persistencia/eventos.py does not import forbidden modules."""
    for node in ast.walk(TREE):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_mod = alias.name.split(".")[0]
                assert alias.name in ALLOWED_MODULES or root_mod in ALLOWED_MODULES, (
                    f"Disallowed import: {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom) and node.module:
            root_mod = node.module.split(".")[0]
            assert node.module in ALLOWED_MODULES or root_mod in ALLOWED_MODULES, (
                f"Disallowed from-import: {node.module}"
            )


def test_payload_models_exist_and_forbid_extra():
    """Verify all 12 TipoEvento values have a Pydantic model with extra='forbid'."""
    assert len(eventos.PAYLOAD_POR_TIPO) == 12
    for tipo in TipoEvento:
        assert tipo in eventos.PAYLOAD_POR_TIPO, f"Missing payload model for {tipo}"
        model = eventos.PAYLOAD_POR_TIPO[tipo]
        assert issubclass(model, BaseModel)
        assert model.model_config.get("extra") == "forbid"


def test_registrar_evento_signature():
    """Verify signature of registrar_evento matches R3 contract."""
    sig = inspect.signature(eventos.registrar_evento)
    params = list(sig.parameters.keys())
    assert params == [
        "conn",
        "fazenda_id",
        "tipo",
        "origem",
        "ocorrido_em",
        "payload",
        "ator",
        "corrige_evento_id",
        "chave_idempotencia",
    ]
    assert sig.parameters["ator"].default is None
    assert sig.parameters["corrige_evento_id"].default is None
    assert sig.parameters["chave_idempotencia"].default is None


# ==============================================================================
# Functional & Hidden Tests (KIT-ACEITE-005)
# ==============================================================================


def test_case_given_in_spec_leitura_satelite():
    """Worked example: valid satellite reading passes, pixels_validos=0 fails."""
    valid_payload = {
        "entidade_id": uuid.uuid4(),
        "piquete_id": uuid.uuid4(),
        "data": date(2026, 9, 10),
        "ndvi": 0.72,
        "origem_ndvi": "sentinel-2",
        "pct_nuvem": 5.0,
        "pixels_validos": 120,
        "massa_kg_ms_ha": 4000.0,
        "taxa_acumulo_kg_ms_ha_dia": 50.0,
        "confianca": "alta",
    }
    validated = eventos.PayloadLeituraSatelite.model_validate(valid_payload)
    assert validated.ndvi == 0.72

    # pixels_validos=0 must raise ValidationError (gt=0)
    invalid_payload = {**valid_payload, "pixels_validos": 0}
    with pytest.raises(ValidationError):
        eventos.PayloadLeituraSatelite.model_validate(invalid_payload)


def test_hidden_case_1_invalid_composition():
    """Hidden Case 1: ComposicaoPayload with n_animais=0 must raise ValidationError."""
    with pytest.raises(ValidationError):
        eventos.ComposicaoPayload(categoria="adulto", n_animais=0, peso_medio_kg=450.0)

    # Valid composition
    comp = eventos.ComposicaoPayload(categoria="adulto", n_animais=10, peso_medio_kg=450.0)
    assert comp.n_animais == 10


def test_hidden_case_2_wrong_payload_type():
    """Hidden Case 2: Payload with only entidade_id passes for dissolvido, fails for alterado."""
    minimal_payload = {"entidade_id": uuid.uuid4()}

    # Should pass for lote_dissolvido
    dissolvido = eventos.PayloadLoteDissolvido.model_validate(minimal_payload)
    assert dissolvido.entidade_id == minimal_payload["entidade_id"]

    # Should fail for lote_alterado (missing nome, composicao, indissoluvel, ativo)
    with pytest.raises(ValidationError):
        eventos.PayloadLoteAlterado.model_validate(minimal_payload)


def test_hidden_case_3_idempotency_with_db():
    """Hidden Case 3: Idempotent writes with same chave_idempotencia return same id.

    Skipped if SEUGADO_TEST_DATABASE_URL is not set.
    """
    db_url = os.environ.get("SEUGADO_TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("SEUGADO_TEST_DATABASE_URL not set; skipping live DB idempotency test")

    import psycopg

    conn = psycopg.connect(db_url)
    try:
        fazenda_id = uuid.uuid4()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO fazenda (id) VALUES (%s)", (fazenda_id,))

        chave = f"conf-{uuid.uuid4()}"
        payload = {
            "entidade_id": uuid.uuid4(),
            "nome": "Piquete Conformance",
            "area_ha": 10.0,
            "cultivar_id": uuid.uuid4(),
            "metodo_pastejo": "rotacionado",
            "ativo": True,
        }

        id_1 = eventos.registrar_evento(
            conn,
            fazenda_id,
            TipoEvento.PIQUETE_CRIADO,
            OrigemEvento.PRODUTOR,
            datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
            payload,
            chave_idempotencia=chave,
        )

        id_2 = eventos.registrar_evento(
            conn,
            fazenda_id,
            TipoEvento.PIQUETE_CRIADO,
            OrigemEvento.PRODUTOR,
            datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
            payload,
            chave_idempotencia=chave,
        )

        assert id_1 == id_2, "Idempotent calls returned different UUIDs"

        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM evento WHERE fazenda_id = %s AND chave_idempotencia = %s",
                (fazenda_id, chave),
            )
            row = cur.fetchone()
            assert row is not None and row[0] == 1, "Duplicate event row found for unique key"
    finally:
        conn.rollback()
        conn.close()
