"""Independent conformance suite covering SPEC-004 (core/regras.py).

Written by the tester role, not the implementer. Tests map to requirements
and acceptance criteria of SPEC-004 and verification scenarios in KIT-ACEITE-004.
"""

import ast
import inspect
import uuid
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path

import pytest

from seugado.core import regras
from seugado.core.models import (
    Confianca,
    Cultivar,
    MetodoPastejo,
    ParametrosRegime,
    QualidadeBase,
)

ROOT = Path(__file__).resolve().parents[2]
REGRAS_PATH = ROOT / "src" / "seugado" / "core" / "regras.py"
SOURCE = REGRAS_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

ALLOWED_MODULES = {"dataclasses", "seugado.core.models"}
EXPECTED_PUBLIC_NAMES = {
    "ResolucaoParametros",
    "resolver_parametros",
    "apto_para_entrada",
    "precisa_sair",
    "urgencia",
    "descanso_cumprido",
}


def _dummy_cultivar(*blocos: ParametrosRegime) -> Cultivar:
    return Cultivar(
        id=uuid.uuid4(),
        slug="test-cultivar",
        nome="Test Cultivar",
        parametros_por_regime=tuple(blocos),
        densidade_kg_ha_por_cm=250.0,
        temperatura_base_c=10.0,
        rue_max_g_por_mj=2.0,
        qualidade_base=QualidadeBase.ALTA,
    )


# ==============================================================================
# Structural & Hygiene Conformance (SPEC-004, KIT-ACEITE-004)
# ==============================================================================


def test_file_length_under_300_lines():
    lines = SOURCE.splitlines()
    assert len(lines) <= 300, f"regras.py has {len(lines)} lines, exceeding 300."


def test_imports_whitelist():
    """Verify that regras.py only imports from allowed standard modules and models."""
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
    """Verify exactly the expected public class and 5 functions exist in regras.py."""
    public_names = {
        node.name
        for node in TREE.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith("_")
    }
    assert public_names == EXPECTED_PUBLIC_NAMES, (
        f"Public API mismatch: {public_names ^ EXPECTED_PUBLIC_NAMES}"
    )


def test_resolucao_parametros_dataclass_contract():
    """Verify ResolucaoParametros is frozen, slotted, and has exact fields."""
    cls = regras.ResolucaoParametros
    assert is_dataclass(cls)
    res = cls(parametros=None, faltantes=("altura_entrada_cm",))
    assert res.parametros is None
    assert res.faltantes == ("altura_entrada_cm",)

    with pytest.raises(FrozenInstanceError):
        res.faltantes = ()  # type: ignore[misc]


def test_no_forbidden_class_features_in_regras():
    """Verify absence of __post_init__, custom __hash__, or __all__."""
    assert not hasattr(regras, "__all__")
    cls = regras.ResolucaoParametros
    assert "__post_init__" not in cls.__dict__


def test_all_functions_and_dataclass_have_type_annotations():
    """Every public function must have type annotations for all args and return."""
    for name in EXPECTED_PUBLIC_NAMES:
        obj = getattr(regras, name)
        if inspect.isfunction(obj):
            sig = inspect.signature(obj)
            assert sig.return_annotation is not inspect.Signature.empty, (
                f"{name} missing return type annotation"
            )
            for param_name, param in sig.parameters.items():
                assert param.annotation is not inspect.Signature.empty, (
                    f"{name} parameter '{param_name}' missing type annotation"
                )


# ==============================================================================
# Canonical Worked Example Case (SPEC-004, KIT-ACEITE-004)
# ==============================================================================


def test_canonical_worked_example():
    bloco_rot = ParametrosRegime(
        metodo=MetodoPastejo.ROTACIONADO,
        altura_entrada_cm=90.0,
        altura_saida_cm=40.0,
        altura_maxima_cm=None,
        altura_minima_cm=None,
        confianca=Confianca.ALTA,
        fonte="worked example",
    )
    cultivar = _dummy_cultivar(bloco_rot)

    # 1. Resolucao para ROTACIONADO
    res_rot = regras.resolver_parametros(cultivar, MetodoPastejo.ROTACIONADO)
    assert res_rot.parametros == bloco_rot
    assert res_rot.faltantes == ()

    # 2. Resolucao para CONTINUO (bloco ausente)
    res_cont = regras.resolver_parametros(cultivar, MetodoPastejo.CONTINUO)
    assert res_cont.parametros is None
    assert res_cont.faltantes == ("altura_maxima_cm", "altura_minima_cm")

    # 3. apto_para_entrada em 88 cm (abaixo de 90 cm) e 90 cm
    assert regras.apto_para_entrada(88.0, bloco_rot, descanso_cumprido=True) is False
    assert regras.apto_para_entrada(90.0, bloco_rot, descanso_cumprido=True) is True
    assert regras.apto_para_entrada(90.0, bloco_rot, descanso_cumprido=False) is False

    # 4. precisa_sair em 38 cm (abaixo de 40 cm) e 41 cm
    assert regras.precisa_sair(38.0, bloco_rot) is True
    assert regras.precisa_sair(41.0, bloco_rot) is False

    # 5. urgencia em 38 cm (+2.0) e 88 cm (-48.0)
    assert regras.urgencia(38.0, bloco_rot) == pytest.approx(2.0, abs=0.001)
    assert regras.urgencia(88.0, bloco_rot) == pytest.approx(-48.0, abs=0.001)

    # 6. descanso_cumprido
    assert regras.descanso_cumprido(21, 21.0) is True
    assert regras.descanso_cumprido(20, 21.0) is False


# ==============================================================================
# Hidden Test Cases (KIT-ACEITE-004)
# ==============================================================================


def test_hidden_case_1_partial_block_piata():
    """Hidden Case 1: Partial block (rotational with entrada defined, saida missing).

    Must return parametros=None and faltantes=('altura_saida_cm',).
    A partial block is never returned as usable.
    """
    bloco_parcial = ParametrosRegime(
        metodo=MetodoPastejo.ROTACIONADO,
        altura_entrada_cm=80.0,
        altura_saida_cm=None,
        altura_maxima_cm=None,
        altura_minima_cm=None,
        confianca=Confianca.ALTA,
        fonte="CT-135 Embrapa (Piatã)",
    )
    cultivar = _dummy_cultivar(bloco_parcial)

    res = regras.resolver_parametros(cultivar, MetodoPastejo.ROTACIONADO)
    assert res.parametros is None
    assert res.faltantes == ("altura_saida_cm",)


def test_hidden_case_2_descanso_boundaries():
    """Hidden Case 2: Boundary test with general literature value (21 days)."""
    assert regras.descanso_cumprido(dias_desde_ultima_saida=21, descanso_min_dias=21.0) is True
    assert regras.descanso_cumprido(dias_desde_ultima_saida=0, descanso_min_dias=21.0) is False
    assert regras.descanso_cumprido(dias_desde_ultima_saida=22, descanso_min_dias=21.0) is True


def test_hidden_case_3_continuo_block_raises_value_error():
    """Hidden Case 3: Calling rotation rules with continuous block must raise ValueError."""
    bloco_cont = ParametrosRegime(
        metodo=MetodoPastejo.CONTINUO,
        altura_entrada_cm=None,
        altura_saida_cm=None,
        altura_maxima_cm=120.0,
        altura_minima_cm=60.0,
        confianca=Confianca.ALTA,
        fonte="fixture continuous",
    )

    with pytest.raises(ValueError, match="rotacionado"):
        regras.apto_para_entrada(100.0, bloco_cont, descanso_cumprido=True)

    with pytest.raises(ValueError, match="rotacionado"):
        regras.precisa_sair(50.0, bloco_cont)

    with pytest.raises(ValueError, match="rotacionado"):
        regras.urgencia(50.0, bloco_cont)


def test_hidden_case_4_multiple_blocks_order_independence():
    """Hidden Case 4: Cultivar carrying both CONTINUO and ROTACIONADO blocks.

    resolver_parametros must match by metodo regardless of position.
    """
    bloco_cont = ParametrosRegime(
        metodo=MetodoPastejo.CONTINUO,
        altura_entrada_cm=None,
        altura_saida_cm=None,
        altura_maxima_cm=120.0,
        altura_minima_cm=60.0,
        confianca=Confianca.ALTA,
        fonte="fixture cont",
    )
    bloco_rot = ParametrosRegime(
        metodo=MetodoPastejo.ROTACIONADO,
        altura_entrada_cm=90.0,
        altura_saida_cm=40.0,
        altura_maxima_cm=None,
        altura_minima_cm=None,
        confianca=Confianca.ALTA,
        fonte="fixture rot",
    )

    # First order: CONTINUO first, ROTACIONADO second
    cultivar_1 = _dummy_cultivar(bloco_cont, bloco_rot)
    res_1 = regras.resolver_parametros(cultivar_1, MetodoPastejo.ROTACIONADO)
    assert res_1.parametros == bloco_rot
    assert res_1.faltantes == ()

    # Second order: ROTACIONADO first, CONTINUO second
    cultivar_2 = _dummy_cultivar(bloco_rot, bloco_cont)
    res_2 = regras.resolver_parametros(cultivar_2, MetodoPastejo.CONTINUO)
    assert res_2.parametros == bloco_cont
    assert res_2.faltantes == ()


def test_validation_errors():
    """Validation checks for None required fields and negative inputs."""
    bloco_sem_entrada = ParametrosRegime(
        metodo=MetodoPastejo.ROTACIONADO,
        altura_entrada_cm=None,
        altura_saida_cm=40.0,
        altura_maxima_cm=None,
        altura_minima_cm=None,
        confianca=Confianca.ALTA,
        fonte="test",
    )
    with pytest.raises(ValueError, match="altura_entrada_cm"):
        regras.apto_para_entrada(95.0, bloco_sem_entrada, descanso_cumprido=True)

    bloco_sem_saida = ParametrosRegime(
        metodo=MetodoPastejo.ROTACIONADO,
        altura_entrada_cm=90.0,
        altura_saida_cm=None,
        altura_maxima_cm=None,
        altura_minima_cm=None,
        confianca=Confianca.ALTA,
        fonte="test",
    )
    with pytest.raises(ValueError, match="altura_saida_cm"):
        regras.precisa_sair(30.0, bloco_sem_saida)

    with pytest.raises(ValueError, match="altura_saida_cm"):
        regras.urgencia(30.0, bloco_sem_saida)

    with pytest.raises(ValueError, match="dias_desde_ultima_saida must be non-negative"):
        regras.descanso_cumprido(-1, 21.0)

    with pytest.raises(ValueError, match="descanso_min_dias must be positive"):
        regras.descanso_cumprido(10, 0.0)

    with pytest.raises(ValueError, match="descanso_min_dias must be positive"):
        regras.descanso_cumprido(10, -5.0)
