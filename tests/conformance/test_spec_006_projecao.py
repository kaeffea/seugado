"""Independent conformance suite covering SPEC-006 (core/projecao.py).

Written by the tester role, not the implementer. Tests map to requirements
and acceptance criteria of SPEC-006 and verification scenarios in KIT-ACEITE-006.
"""

import ast
import inspect
import uuid
from dataclasses import is_dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from seugado.core.models import (
    Evento,
    MetodoPastejo,
    OrigemEvento,
    TipoEvento,
)
from seugado.core.projecao import (
    EstadoFazenda,
    EstadoLote,
    EstadoPiquete,
    Leitura,
    SituacaoPiquete,
    projetar,
)

ROOT = Path(__file__).resolve().parents[2]
PROJECAO_PATH = ROOT / "src" / "seugado" / "core" / "projecao.py"
SOURCE = PROJECAO_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

ALLOWED_MODULES = {
    "collections.abc",
    "dataclasses",
    "datetime",
    "enum",
    "typing",
    "uuid",
    "seugado.core.models",
}

EXPECTED_PUBLIC_NAMES = {
    "SituacaoPiquete",
    "EstadoPiquete",
    "EstadoLote",
    "Leitura",
    "EstadoFazenda",
    "projetar",
}


# ==============================================================================
# Structural & Hygiene Conformance (SPEC-006, KIT-ACEITE-006)
# ==============================================================================


def test_file_length_under_300_lines():
    lines = SOURCE.splitlines()
    assert len(lines) <= 300, f"projecao.py has {len(lines)} lines, exceeding 300."


def test_imports_whitelist():
    """Verify that projecao.py only imports from allowed stdlib and models."""
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


def test_public_api_exact_match():
    """Verify exactly the expected public class/enum and function names exist."""
    public_names = {
        node.name
        for node in TREE.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith("_")
    }
    assert public_names == EXPECTED_PUBLIC_NAMES, (
        f"Public API mismatch: {public_names ^ EXPECTED_PUBLIC_NAMES}"
    )


def test_situacao_piquete_enum():
    assert [m.value for m in SituacaoPiquete] == ["ocupado", "descansando"]


def test_dataclasses_frozen_and_slotted():
    for cls in (EstadoPiquete, EstadoLote, Leitura, EstadoFazenda):
        assert is_dataclass(cls)
        assert getattr(cls, "__slots__", None) is not None, f"{cls} missing __slots__"


def test_estado_piquete_fields_exact():
    expected_fields = [
        "piquete_id",
        "fazenda_id",
        "nome",
        "area_ha",
        "cultivar_id",
        "metodo_pastejo",
        "ativo",
        "situacao",
        "lote_atual_id",
        "desde",
        "dias_descanso",
    ]
    actual_fields = list(inspect.signature(EstadoPiquete).parameters.keys())
    assert actual_fields == expected_fields
    assert "massa_kg_ms_ha" not in actual_fields
    assert "aguardando_parametro" not in actual_fields


def test_projetar_signature():
    sig = inspect.signature(projetar)
    assert list(sig.parameters.keys()) == ["eventos"]
    assert sig.return_annotation is EstadoFazenda


# ==============================================================================
# Canonical and Correction Cases (SPEC-006, KIT-ACEITE-006)
# ==============================================================================

FAZENDA_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CULTIVAR_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
P1_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
L1_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _make_evento(
    tipo: TipoEvento,
    ocorrido_em: datetime,
    sequencia: int,
    payload: dict[str, object],
    evento_id: uuid.UUID | None = None,
    corrige_id: uuid.UUID | None = None,
) -> Evento:
    return Evento(
        id=evento_id or uuid.uuid4(),
        fazenda_id=FAZENDA_ID,
        tipo=tipo,
        ocorrido_em=ocorrido_em,
        registrado_em=ocorrido_em,
        payload=payload,
        origem=OrigemEvento.PRODUTOR,
        sequencia=sequencia,
        corrige_evento_id=corrige_id,
    )


def test_canonical_case():
    e1 = _make_evento(
        tipo=TipoEvento.PIQUETE_CRIADO,
        ocorrido_em=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        sequencia=1,
        payload={
            "entidade_id": P1_ID,
            "nome": "P1",
            "area_ha": 5.81,
            "cultivar_id": CULTIVAR_ID,
            "metodo_pastejo": MetodoPastejo.ROTACIONADO.value,
            "ativo": True,
        },
    )
    e2 = _make_evento(
        tipo=TipoEvento.LOTE_CRIADO,
        ocorrido_em=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
        sequencia=2,
        payload={
            "entidade_id": L1_ID,
            "nome": "L1",
            "composicao": [
                {"categoria": "adulto", "n_animais": 20, "peso_medio_kg": 450.0},
            ],
            "indissoluvel": False,
        },
    )
    e3 = _make_evento(
        tipo=TipoEvento.MANEJO_CONFIRMADO,
        ocorrido_em=datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
        sequencia=3,
        payload={
            "entidade_id": uuid.uuid4(),
            "lote_id": L1_ID,
            "piquete_destino_id": P1_ID,
            "data_execucao": "2026-09-10",
        },
    )

    estado = projetar([e1, e2, e3])

    p1 = estado.piquetes[P1_ID]
    assert p1.situacao == SituacaoPiquete.OCUPADO
    assert p1.lote_atual_id == L1_ID
    assert p1.desde == date(2026, 9, 10)
    assert p1.dias_descanso == 0

    l1 = estado.lotes[L1_ID]
    assert l1.piquete_atual_id == P1_ID
    assert l1.peso_vivo_total_kg == pytest.approx(9000.0)


def test_correction_case_applies_at_original_position():
    e1_id = uuid.uuid4()
    e1 = _make_evento(
        tipo=TipoEvento.PIQUETE_CRIADO,
        ocorrido_em=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        sequencia=1,
        payload={
            "entidade_id": P1_ID,
            "nome": "P1",
            "area_ha": 5.81,
            "cultivar_id": CULTIVAR_ID,
            "metodo_pastejo": MetodoPastejo.ROTACIONADO.value,
            "ativo": True,
        },
        evento_id=e1_id,
    )
    e2 = _make_evento(
        tipo=TipoEvento.LOTE_CRIADO,
        ocorrido_em=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
        sequencia=2,
        payload={
            "entidade_id": L1_ID,
            "nome": "L1",
            "composicao": [
                {"categoria": "adulto", "n_animais": 20, "peso_medio_kg": 450.0},
            ],
            "indissoluvel": False,
        },
    )
    e3 = _make_evento(
        tipo=TipoEvento.MANEJO_CONFIRMADO,
        ocorrido_em=datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
        sequencia=3,
        payload={
            "entidade_id": uuid.uuid4(),
            "lote_id": L1_ID,
            "piquete_destino_id": P1_ID,
            "data_execucao": "2026-09-10",
        },
    )
    # Correction event emitted on 2026-09-15 correcting e1
    e_corr = _make_evento(
        tipo=TipoEvento.PIQUETE_CRIADO,
        ocorrido_em=datetime(2026, 9, 15, 8, 0, tzinfo=UTC),
        sequencia=4,
        payload={
            "entidade_id": P1_ID,
            "nome": "P1",
            "area_ha": 6.02,
            "cultivar_id": CULTIVAR_ID,
            "metodo_pastejo": MetodoPastejo.ROTACIONADO.value,
            "ativo": True,
        },
        corrige_id=e1_id,
    )

    estado = projetar([e1, e2, e3, e_corr])
    assert estado.piquetes[P1_ID].area_ha == pytest.approx(6.02)
    # Piquete remains occupied by L1
    assert estado.piquetes[P1_ID].situacao == SituacaoPiquete.OCUPADO
    assert estado.piquetes[P1_ID].lote_atual_id == L1_ID


# ==============================================================================
# Hidden Test Cases (KIT-ACEITE-006)
# ==============================================================================


def test_hidden_case_1_dissolucao_durante_ocupacao():
    """Hidden Case 1: Dissolution during occupation sets piquete to resting at dissolution date."""
    e1 = _make_evento(
        tipo=TipoEvento.PIQUETE_CRIADO,
        ocorrido_em=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        sequencia=1,
        payload={
            "entidade_id": P1_ID,
            "nome": "P1",
            "area_ha": 5.0,
            "cultivar_id": CULTIVAR_ID,
            "metodo_pastejo": MetodoPastejo.ROTACIONADO.value,
            "ativo": True,
        },
    )
    e2 = _make_evento(
        tipo=TipoEvento.LOTE_CRIADO,
        ocorrido_em=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
        sequencia=2,
        payload={
            "entidade_id": L1_ID,
            "nome": "L1",
            "composicao": [{"categoria": "novilho", "n_animais": 10, "peso_medio_kg": 300.0}],
            "indissoluvel": False,
        },
    )
    e3 = _make_evento(
        tipo=TipoEvento.MANEJO_CONFIRMADO,
        ocorrido_em=datetime(2026, 9, 3, 8, 0, tzinfo=UTC),
        sequencia=3,
        payload={
            "entidade_id": uuid.uuid4(),
            "lote_id": L1_ID,
            "piquete_destino_id": P1_ID,
            "data_execucao": "2026-09-03",
        },
    )
    e4 = _make_evento(
        tipo=TipoEvento.LOTE_DISSOLVIDO,
        ocorrido_em=datetime(2026, 9, 8, 12, 0, tzinfo=UTC),
        sequencia=4,
        payload={"entidade_id": L1_ID},
    )

    estado = projetar([e1, e2, e3, e4])

    assert L1_ID not in estado.lotes
    p1 = estado.piquetes[P1_ID]
    assert p1.situacao == SituacaoPiquete.DESCANSANDO
    assert p1.lote_atual_id is None
    assert p1.desde == date(2026, 9, 8)
    assert p1.dias_descanso == 0  # data_referencia is 2026-09-08


def test_hidden_case_2_two_independent_corrections():
    """Hidden Case 2: Two independent corrections on two distinct piquetes."""
    p2_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    e1_id = uuid.uuid4()
    e2_id = uuid.uuid4()

    e1 = _make_evento(
        tipo=TipoEvento.PIQUETE_CRIADO,
        ocorrido_em=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        sequencia=1,
        payload={
            "entidade_id": P1_ID,
            "nome": "P1",
            "area_ha": 5.0,
            "cultivar_id": CULTIVAR_ID,
            "metodo_pastejo": MetodoPastejo.ROTACIONADO.value,
            "ativo": True,
        },
        evento_id=e1_id,
    )
    e2 = _make_evento(
        tipo=TipoEvento.PIQUETE_CRIADO,
        ocorrido_em=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
        sequencia=2,
        payload={
            "entidade_id": p2_id,
            "nome": "P2",
            "area_ha": 10.0,
            "cultivar_id": CULTIVAR_ID,
            "metodo_pastejo": MetodoPastejo.ROTACIONADO.value,
            "ativo": True,
        },
        evento_id=e2_id,
    )
    corr1 = _make_evento(
        tipo=TipoEvento.PIQUETE_CRIADO,
        ocorrido_em=datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
        sequencia=3,
        payload={
            "entidade_id": P1_ID,
            "nome": "P1-Corrigido",
            "area_ha": 5.5,
            "cultivar_id": CULTIVAR_ID,
            "metodo_pastejo": MetodoPastejo.ROTACIONADO.value,
            "ativo": True,
        },
        corrige_id=e1_id,
    )
    corr2 = _make_evento(
        tipo=TipoEvento.PIQUETE_CRIADO,
        ocorrido_em=datetime(2026, 9, 11, 8, 0, tzinfo=UTC),
        sequencia=4,
        payload={
            "entidade_id": p2_id,
            "nome": "P2-Corrigido",
            "area_ha": 11.2,
            "cultivar_id": CULTIVAR_ID,
            "metodo_pastejo": MetodoPastejo.ROTACIONADO.value,
            "ativo": True,
        },
        corrige_id=e2_id,
    )

    estado = projetar([e1, e2, corr1, corr2])
    assert estado.piquetes[P1_ID].nome == "P1-Corrigido"
    assert estado.piquetes[P1_ID].area_ha == 5.5
    assert estado.piquetes[p2_id].nome == "P2-Corrigido"
    assert estado.piquetes[p2_id].area_ha == 11.2


def test_hidden_case_3_reference_to_unknown_entity_raises():
    """Hidden Case 3: References to nonexistent entities raise ValueError."""
    # Unknown lote in lote_alterado
    e_lote_alt = _make_evento(
        tipo=TipoEvento.LOTE_ALTERADO,
        ocorrido_em=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        sequencia=1,
        payload={
            "entidade_id": uuid.uuid4(),
            "nome": "Unknown Lote",
            "composicao": [],
            "indissoluvel": False,
        },
    )
    with pytest.raises(ValueError, match="unknown lote"):
        projetar([e_lote_alt])

    # Manejo confirmado with unknown piquete_destino_id
    e_lote_ok = _make_evento(
        tipo=TipoEvento.LOTE_CRIADO,
        ocorrido_em=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        sequencia=1,
        payload={
            "entidade_id": L1_ID,
            "nome": "L1",
            "composicao": [],
            "indissoluvel": False,
        },
    )
    e_man_dest_unknown = _make_evento(
        tipo=TipoEvento.MANEJO_CONFIRMADO,
        ocorrido_em=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
        sequencia=2,
        payload={
            "entidade_id": uuid.uuid4(),
            "lote_id": L1_ID,
            "piquete_destino_id": uuid.uuid4(),
            "data_execucao": "2026-09-02",
        },
    )
    with pytest.raises(ValueError, match="unknown piquete"):
        projetar([e_lote_ok, e_man_dest_unknown])


def test_hidden_case_4_events_without_effect_pass_through():
    """Hidden Case 4: Events without projection effect are silently ignored."""
    e1 = _make_evento(
        tipo=TipoEvento.PIQUETE_CRIADO,
        ocorrido_em=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        sequencia=1,
        payload={
            "entidade_id": P1_ID,
            "nome": "P1",
            "area_ha": 5.0,
            "cultivar_id": CULTIVAR_ID,
            "metodo_pastejo": MetodoPastejo.ROTACIONADO.value,
            "ativo": True,
        },
    )
    e_no_effect = _make_evento(
        tipo=TipoEvento.PARAMETRO_ALTERADO,
        ocorrido_em=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
        sequencia=2,
        payload={"chave": "valor", "qualquer": 123},
    )

    estado = projetar([e1, e_no_effect])
    assert P1_ID in estado.piquetes
    assert len(estado.lotes) == 0
