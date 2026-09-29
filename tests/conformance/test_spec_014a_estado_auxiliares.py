"""Independent conformance suite covering SPEC-014A (Auxiliares do estado).

Written by the tester role (Antigravity), not the implementer.
Tests map to requirements of SPEC-014A and verification scenarios in KIT-ACEITE-014A.
"""

import ast
from pathlib import Path

import pytest

from seugado.core.models import CategoriaAnimal, ComposicaoLote, Confianca, OrigemPeso
from seugado.planner import estado

ROOT = Path(__file__).resolve().parents[2]
ESTADO_PY = ROOT / "src" / "seugado" / "planner" / "estado.py"
CARGA_PY = ROOT / "src" / "seugado" / "planner" / "carga.py"


# ==============================================================================
# Structural Checks (KIT-ACEITE-014A)
# ==============================================================================



def test_estado_py_forbidden_imports() -> None:
    """planner/estado.py must not import psycopg, httpx, ee, sensing, persistencia, api."""
    content = ESTADO_PY.read_text(encoding="utf-8")
    tree = ast.parse(content)
    forbidden = ("psycopg", "httpx", "ee", "sensing", "persistencia", "api")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(alias.name.startswith(f) for f in forbidden), (
                    f"Forbidden import: {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not any(node.module.startswith(f) for f in forbidden), (
                f"Forbidden import from: {node.module}"
            )


def test_expected_symbols_exist() -> None:
    """All required constants and functions must exist on planner/estado.py."""
    expected_symbols = (
        "CONSUMO_FRACAO_PV",
        "UA_POR_CATEGORIA",
        "UNIDADE_ANIMAL_KG",
        "peso_por_ua_kg",
        "consumo_lote",
        "confianca_peso",
        "avancar_massa_um_dia",
        "confianca_estimativa",
    )
    for sym in expected_symbols:
        assert hasattr(estado, sym), f"Missing symbol in estado.py: {sym}"


def test_constants_values() -> None:
    """Constants must match exact domain specifications."""
    assert estado.UNIDADE_ANIMAL_KG == 450.0
    assert estado.CONSUMO_FRACAO_PV == {
        CategoriaAnimal.BEZERRO: 0.024,
        CategoriaAnimal.BEZERRA: 0.024,
        CategoriaAnimal.NOVILHO: 0.022,
        CategoriaAnimal.NOVILHA: 0.022,
        CategoriaAnimal.VACA: 0.024,
        CategoriaAnimal.BOI: 0.024,
        CategoriaAnimal.TOURO: 0.024,
    }
    assert estado.UA_POR_CATEGORIA == {
        CategoriaAnimal.BEZERRO: 0.25,
        CategoriaAnimal.BEZERRA: 0.25,
        CategoriaAnimal.NOVILHO: 0.75,
        CategoriaAnimal.NOVILHA: 0.75,
        CategoriaAnimal.VACA: 1.00,
        CategoriaAnimal.BOI: 1.00,
        CategoriaAnimal.TOURO: 1.25,
    }


# ==============================================================================
# Canonical Cases (KIT-ACEITE-014A)
# ==============================================================================


def test_canonical_worked_examples() -> None:
    """Worked examples from spec: 337.5, 1113.75, 2038.04, and confidence by ruler."""
    # 1. Novilho fallback weight
    assert estado.peso_por_ua_kg(CategoriaAnimal.NOVILHO) == pytest.approx(337.5)

    # 2. Intake for 150 novilhos of 337.5 kg
    comp = (ComposicaoLote(CategoriaAnimal.NOVILHO, 150, 337.5, OrigemPeso.UA_TABELA),)
    assert estado.consumo_lote(comp) == pytest.approx(1113.75)

    # 3. Forage stock forward step: 2420 + 60 - 1113.75 / (0.72 * 3.5) = 2038.0357...
    res = estado.avancar_massa_um_dia(
        massa_kg_ms_ha=2420.0,
        taxa_acumulo_kg_ms_ha_dia=60.0,
        consumo_lote_kg_ms_dia=1113.75,
        area_ha=3.5,
        eficiencia_pastejo=0.72,
    )
    assert res == pytest.approx(2038.04, abs=0.01)

    # 4. Confidence: image 3d (ALTA), pixels 40 (ALTA), ruler 20d (MEDIA), unconfirmed False (ALTA)
    # Result is MEDIA, ruler is first factor matching MEDIA
    nivel, frase = estado.confianca_estimativa(
        dias_desde_imagem=3,
        pixels_validos=40,
        dias_desde_altura=20,
        posicao_por_omissao=False,
    )
    assert nivel == Confianca.MEDIA
    assert frase == "última medição de altura há 20 dias"


# ==============================================================================
# Hidden Cases (KIT-ACEITE-014A)
# ==============================================================================


def test_hidden_case_1_avancar_massa_sem_consumo() -> None:
    """Caso 1: avancar_massa_um_dia(2000, 50, 0, 4, None) -> 2050."""
    res = estado.avancar_massa_um_dia(
        massa_kg_ms_ha=2000.0,
        taxa_acumulo_kg_ms_ha_dia=50.0,
        consumo_lote_kg_ms_dia=0.0,
        area_ha=4.0,
        eficiencia_pastejo=None,
    )
    assert res == pytest.approx(2050.0)


def test_hidden_case_2_avancar_massa_floor_zero() -> None:
    """Caso 2: avancar_massa_um_dia(100, 0, 1000, 1, 0.5) -> 0.0 (nao fica negativo)."""
    # 100 + 0 - 1000 / (0.5 * 1) = 100 - 2000 = -1900 -> 0.0
    res = estado.avancar_massa_um_dia(
        massa_kg_ms_ha=100.0,
        taxa_acumulo_kg_ms_ha_dia=0.0,
        consumo_lote_kg_ms_dia=1000.0,
        area_ha=1.0,
        eficiencia_pastejo=0.5,
    )
    assert res == pytest.approx(0.0)


def test_hidden_case_3_confianca_sem_imagem_satelite() -> None:
    """Caso 3: confianca_estimativa(None, None, 50, True) -> BAIXA com frase de sem imagem."""
    nivel, frase = estado.confianca_estimativa(
        dias_desde_imagem=None,
        pixels_validos=None,
        dias_desde_altura=50,
        posicao_por_omissao=True,
    )
    assert nivel == Confianca.BAIXA
    assert frase == "nenhuma imagem de satélite sem nuvem nos últimos 30 dias"


def test_hidden_case_4_confianca_imagem_de_hoje() -> None:
    """Caso 4: confianca_estimativa(0, 12, 1, False) -> ALTA com frase de hoje."""
    nivel, frase = estado.confianca_estimativa(
        dias_desde_imagem=0,
        pixels_validos=12,
        dias_desde_altura=1,
        posicao_por_omissao=False,
    )
    assert nivel == Confianca.ALTA
    assert frase == "última imagem de satélite sem nuvem de hoje"


def test_hidden_case_5_confianca_peso_mista() -> None:
    """Caso 5: confianca_peso com um item PRODUTOR e um UA_TABELA -> MEDIA tabela."""
    comp = (
        ComposicaoLote(CategoriaAnimal.VACA, 10, 450.0, OrigemPeso.PRODUTOR),
        ComposicaoLote(CategoriaAnimal.BEZERRO, 5, 112.5, OrigemPeso.UA_TABELA),
    )
    nivel, frase = estado.confianca_peso(comp)
    assert nivel == Confianca.MEDIA
    assert frase == "peso médio estimado pela tabela de Unidade Animal"


def test_avancar_massa_validations() -> None:
    """Validation errors for area_ha and eficiencia_pastejo."""
    with pytest.raises(ValueError, match="area_ha"):
        estado.avancar_massa_um_dia(2000.0, 50.0, 100.0, 0.0, 0.7)

    with pytest.raises(ValueError, match="area_ha"):
        estado.avancar_massa_um_dia(2000.0, 50.0, 100.0, -2.0, 0.7)

    with pytest.raises(ValueError, match="eficiencia_pastejo"):
        estado.avancar_massa_um_dia(2000.0, 50.0, 100.0, 3.0, None)

    with pytest.raises(ValueError, match="eficiencia_pastejo"):
        estado.avancar_massa_um_dia(2000.0, 50.0, 100.0, 3.0, 0.0)

    with pytest.raises(ValueError, match="eficiencia_pastejo"):
        estado.avancar_massa_um_dia(2000.0, 50.0, 100.0, 3.0, 1.2)
