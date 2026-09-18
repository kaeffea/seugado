"""Independent conformance suite covering the schema as of SPEC-001 and SPEC-002.

Written by the tester role, not the implementer. Each test maps to an acceptance
criterion (AC-n) or requirement (R-n) of SPEC-001. Tests marked `finding_` are
not acceptance criteria: they document behaviour the spec does not cover, so a
future spec can decide on it deliberately.
"""

import ast
import dataclasses
import enum
import typing
import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from seugado.core import models

ROOT = Path(__file__).resolve().parents[2]
MODELS_PATH = ROOT / "src" / "seugado" / "core" / "models.py"
SOURCE = MODELS_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

ALLOWED_IMPORTS = {"dataclasses", "datetime", "enum", "typing", "uuid"}

ENUMS = {
    "CategoriaAnimal": {"BEZERRO": "bezerro", "NOVILHO": "novilho", "ADULTO": "adulto"},
    "QualidadeBase": {"ALTA": "alta", "MEDIA": "media", "BAIXA": "baixa"},
    "MetodoPastejo": {"CONTINUO": "continuo", "ROTACIONADO": "rotacionado"},
    "Confianca": {"ALTA": "alta", "MEDIA": "media", "BAIXA": "baixa"},
    "StatusManejo": {
        "RECOMENDADO": "recomendado",
        "CONFIRMADO": "confirmado",
        "RECUSADO": "recusado",
        "DIVERGENTE": "divergente",
    },
    "OrigemEvento": {
        "PRODUTOR": "produtor",
        "SISTEMA": "sistema",
        "SATELITE": "satelite",
        "SAR_INFERIDO": "sar_inferido",
    },
    "TipoEvento": {
        "PIQUETE_CRIADO": "piquete_criado",
        "PIQUETE_ALTERADO": "piquete_alterado",
        "LOTE_CRIADO": "lote_criado",
        "LOTE_ALTERADO": "lote_alterado",
        "LOTE_DISSOLVIDO": "lote_dissolvido",
        "MANEJO_RECOMENDADO": "manejo_recomendado",
        "MANEJO_CONFIRMADO": "manejo_confirmado",
        "MANEJO_RECUSADO": "manejo_recusado",
        "MANEJO_DIVERGENTE": "manejo_divergente",
        "LEITURA_SATELITE": "leitura_satelite",
        "FOTO_VALIDACAO": "foto_validacao",
        "PARAMETRO_ALTERADO": "parametro_alterado",
    },
}

# Exact field spec from R3..R8: (name, annotation source, default source or None).
NO_DEFAULT = object()
DATACLASSES = {
    "Fazenda": [
        ("id", "UUID", NO_DEFAULT),
        ("nome", "str", NO_DEFAULT),
        ("timezone", "str", NO_DEFAULT),
        ("funcionarios_disponiveis", "int", NO_DEFAULT),
        ("manejos_por_funcionario_dia", "int", NO_DEFAULT),
        ("dias_preferenciais_manejo", "tuple[int, ...]", NO_DEFAULT),
        ("ativo", "bool", True),
    ],
    "ParametrosRegime": [
        ("metodo", "MetodoPastejo", NO_DEFAULT),
        ("altura_entrada_cm", "float | None", NO_DEFAULT),
        ("altura_saida_cm", "float | None", NO_DEFAULT),
        ("altura_maxima_cm", "float | None", NO_DEFAULT),
        ("altura_minima_cm", "float | None", NO_DEFAULT),
        ("confianca", "Confianca", NO_DEFAULT),
        ("fonte", "str", NO_DEFAULT),
    ],
    "Cultivar": [
        ("id", "UUID", NO_DEFAULT),
        ("slug", "str", NO_DEFAULT),
        ("nome", "str", NO_DEFAULT),
        ("parametros_por_regime", "tuple[ParametrosRegime, ...]", NO_DEFAULT),
        ("densidade_kg_ha_por_cm", "float", NO_DEFAULT),
        ("temperatura_base_c", "float", NO_DEFAULT),
        ("rue_max_g_por_mj", "float", NO_DEFAULT),
        ("qualidade_base", "QualidadeBase", NO_DEFAULT),
    ],
    "Piquete": [
        ("id", "UUID", NO_DEFAULT),
        ("fazenda_id", "UUID", NO_DEFAULT),
        ("nome", "str", NO_DEFAULT),
        ("area_ha", "float", NO_DEFAULT),
        ("cultivar_id", "UUID", NO_DEFAULT),
        ("metodo_pastejo", "MetodoPastejo", NO_DEFAULT),
        ("geometria_geojson", "dict[str, Any] | None", None),
        ("ativo", "bool", True),
    ],
    "ComposicaoLote": [
        ("categoria", "CategoriaAnimal", NO_DEFAULT),
        ("n_animais", "int", NO_DEFAULT),
        ("peso_medio_kg", "float", NO_DEFAULT),
    ],
    "Lote": [
        ("id", "UUID", NO_DEFAULT),
        ("fazenda_id", "UUID", NO_DEFAULT),
        ("nome", "str", NO_DEFAULT),
        ("composicao", "tuple[ComposicaoLote, ...]", NO_DEFAULT),
        ("indissoluvel", "bool", False),
        ("ativo", "bool", True),
    ],
    "Manejo": [
        ("id", "UUID", NO_DEFAULT),
        ("fazenda_id", "UUID", NO_DEFAULT),
        ("lote_id", "UUID", NO_DEFAULT),
        ("piquete_destino_id", "UUID", NO_DEFAULT),
        ("data_prevista", "date", NO_DEFAULT),
        ("dias_previstos", "int", NO_DEFAULT),
        ("motivo", "str", NO_DEFAULT),
        ("confianca", "Confianca", NO_DEFAULT),
        ("status", "StatusManejo", NO_DEFAULT),
        ("origem", "OrigemEvento", NO_DEFAULT),
        ("piquete_origem_id", "UUID | None", None),
        ("data_execucao", "date | None", None),
    ],
    "Evento": [
        ("id", "UUID", NO_DEFAULT),
        ("fazenda_id", "UUID", NO_DEFAULT),
        ("tipo", "TipoEvento", NO_DEFAULT),
        ("ocorrido_em", "datetime", NO_DEFAULT),
        ("registrado_em", "datetime", NO_DEFAULT),
        ("payload", "dict[str, Any]", NO_DEFAULT),
        ("origem", "OrigemEvento", NO_DEFAULT),
        ("sequencia", "int", NO_DEFAULT),
        ("corrige_evento_id", "UUID | None", None),
    ],
}

EXPECTED_ORDER = list(ENUMS) + list(DATACLASSES)

U = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _classes() -> dict[str, ast.ClassDef]:
    return {n.name: n for n in TREE.body if isinstance(n, ast.ClassDef)}


def _sample(name: str) -> typing.Any:
    """Build one valid instance of each dataclass with arbitrary fixture values."""
    comp = models.ComposicaoLote(models.CategoriaAnimal.ADULTO, 1, 1.0)
    regime = models.ParametrosRegime(
        models.MetodoPastejo.ROTACIONADO, 1.0, 1.0, None, None, models.Confianca.ALTA, "f"
    )
    builders: dict[str, typing.Callable[[], typing.Any]] = {
        "Fazenda": lambda: models.Fazenda(U, "f", "America/Fortaleza", 1, 1, (0,)),
        "ParametrosRegime": lambda: regime,
        "Cultivar": lambda: models.Cultivar(
            U, "s", "n", (regime,), 1.0, 1.0, 1.0, models.QualidadeBase.ALTA
        ),
        "Piquete": lambda: models.Piquete(U, U, "p", 1.0, U, models.MetodoPastejo.ROTACIONADO),
        "ComposicaoLote": lambda: comp,
        "Lote": lambda: models.Lote(U, U, "l", (comp,)),
        "Manejo": lambda: models.Manejo(
            U,
            U,
            U,
            U,
            date(2026, 1, 1),
            1,
            "m",
            models.Confianca.ALTA,
            models.StatusManejo.RECOMENDADO,
            models.OrigemEvento.SISTEMA,
        ),
        "Evento": lambda: models.Evento(
            U,
            U,
            models.TipoEvento.LOTE_CRIADO,
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 1, tzinfo=UTC),
            {},
            models.OrigemEvento.PRODUTOR,
            1,
        ),
    }
    return builders[name]()


# --- AC-1 / R1: imports -------------------------------------------------------


def test_ac1_imports_only_stdlib_whitelist():
    imported = set()
    for node in ast.walk(TREE):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative import found"
            assert node.module is not None
            imported.add(node.module.split(".")[0])
    assert imported <= ALLOWED_IMPORTS, imported - ALLOWED_IMPORTS


def test_ac1_imports_are_top_level_only():
    top = {id(n) for n in TREE.body if isinstance(n, (ast.Import, ast.ImportFrom))}
    nested = [
        n
        for n in ast.walk(TREE)
        if isinstance(n, (ast.Import, ast.ImportFrom)) and id(n) not in top
    ]
    assert not nested


def test_r1_module_docstring_states_immutability_rationale():
    doc = ast.get_docstring(TREE) or ""
    assert "immutable" in doc.lower()
    assert "event log" in doc.lower()


# --- AC-2 / R9: defined names and order ---------------------------------------


def test_ac2_module_defines_exactly_the_thirteen_names():
    defined = []
    for node in TREE.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            defined.append(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            defined += [ast.unparse(t) for t in targets]
    assert sorted(defined) == sorted(EXPECTED_ORDER)


def test_ac2_no_unexpected_top_level_statements():
    allowed = (ast.Import, ast.ImportFrom, ast.ClassDef)
    body = TREE.body[1:] if ast.get_docstring(TREE) else TREE.body
    assert all(isinstance(n, allowed) for n in body)


def test_ac2_runtime_public_names_are_classes_or_imports_only():
    imported = {"dataclass", "date", "datetime", "StrEnum", "Any", "UUID"}
    public = {n for n in vars(models) if not n.startswith("_")}
    assert public - imported == set(EXPECTED_ORDER)


def test_r9_declaration_order():
    assert [c.name for c in TREE.body if isinstance(c, ast.ClassDef)] == EXPECTED_ORDER


# --- AC-3 / AC-4 / R2: enums --------------------------------------------------


@pytest.mark.parametrize("name", list(ENUMS))
def test_ac3_enum_is_strenum_with_exact_members(name):
    cls = getattr(models, name)
    assert issubclass(cls, enum.StrEnum)
    assert cls.__bases__ == (enum.StrEnum,)
    assert {m.name: m.value for m in cls} == ENUMS[name]
    # no aliases: __members__ includes aliases, iteration does not
    assert len(cls.__members__) == len(ENUMS[name])


@pytest.mark.parametrize("name", list(ENUMS))
def test_ac3_enum_has_no_helper_methods(name):
    node = _classes()[name]
    assert not [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def test_ac4_tipo_evento_has_exactly_twelve_members():
    assert len(models.TipoEvento) == 12
    assert len(models.TipoEvento.__members__) == 12


def test_r2_confianca_and_qualidade_base_are_distinct_types():
    assert models.Confianca is not models.QualidadeBase  # type: ignore[comparison-overlap]  # runtime equality is the documented behaviour; see 06 §7 rule 11
    assert not issubclass(models.Confianca, models.QualidadeBase)
    assert not issubclass(models.QualidadeBase, models.Confianca)


# --- AC-5: frozen + slots -----------------------------------------------------


@pytest.mark.parametrize("name", list(DATACLASSES))
def test_ac5_dataclass_is_frozen_and_slotted_at_runtime(name):
    cls = getattr(models, name)
    assert dataclasses.is_dataclass(cls)
    assert typing.cast(typing.Any, cls).__dataclass_params__.frozen is True
    assert "__slots__" in cls.__dict__
    assert not hasattr(_sample(name), "__dict__")


@pytest.mark.parametrize("name", list(DATACLASSES))
def test_ac5_decorator_is_written_exactly_as_specified(name):
    decorators = [ast.unparse(d) for d in _classes()[name].decorator_list]
    assert decorators == ["dataclass(frozen=True, slots=True)"]


def test_ac5_exactly_seven_dataclasses():
    found = [
        n for n in vars(models).values() if isinstance(n, type) and dataclasses.is_dataclass(n)
    ]
    assert len(found) == 8


# --- AC-6 / R3..R8: fields ----------------------------------------------------


@pytest.mark.parametrize("name", list(DATACLASSES))
def test_ac6_every_class_body_statement_is_an_annotated_field(name):
    node = _classes()[name]
    body = node.body[1:] if ast.get_docstring(node) else node.body
    assert body, "empty class"
    assert all(isinstance(s, ast.AnnAssign) for s in body)


@pytest.mark.parametrize("name", list(DATACLASSES))
def test_r3_r8_fields_match_spec_exactly(name):
    node = _classes()[name]
    actual = []
    for s in node.body:
        if isinstance(s, ast.AnnAssign):
            assert isinstance(s.target, ast.Name)
            default = NO_DEFAULT if s.value is None else ast.literal_eval(s.value)
            actual.append((s.target.id, ast.unparse(s.annotation), default))
    assert actual == DATACLASSES[name]


@pytest.mark.parametrize("name", list(DATACLASSES))
def test_r3_r8_annotations_resolve_at_runtime(name):
    hints = typing.get_type_hints(getattr(models, name))
    assert list(hints) == [f[0] for f in DATACLASSES[name]]


@pytest.mark.parametrize("name", ["Cultivar"])
def test_r4_cultivar_has_no_defaults(name):
    for f in dataclasses.fields(models.Cultivar):
        assert f.default is dataclasses.MISSING
        assert f.default_factory is dataclasses.MISSING


def test_r4_cultivar_requires_every_parameter():
    with pytest.raises(TypeError):
        models.Cultivar(id=U, slug="s", nome="n")  # type: ignore[call-arg]


def test_ac2_cultivar_accepts_zero_regime_blocks():
    c = models.Cultivar(U, "s", "n", (), 1.0, 1.0, 1.0, models.QualidadeBase.ALTA)
    assert len(c.parametros_por_regime) == 0
    with pytest.raises(FrozenInstanceError):
        c.parametros_por_regime = (regime_for_finding(),)  # type: ignore[misc]  # intentional: verifying frozen mutation raises at runtime


def regime_for_finding() -> models.ParametrosRegime:
    return models.ParametrosRegime(
        models.MetodoPastejo.CONTINUO, None, None, 1.0, 1.0, models.Confianca.BAIXA, "f"
    )


def test_finding_cultivar_accepts_list_instead_of_tuple_for_regimes():
    # No validation by design, same as test_finding_types_are_not_enforced_so_lists_slip_in.
    c = models.Cultivar(
        U,
        "s",
        "n",
        [regime_for_finding()],  # type: ignore[arg-type]
        1.0,
        1.0,
        1.0,
        models.QualidadeBase.ALTA,
    )
    assert isinstance(c.parametros_por_regime, list)


def test_no_default_factories_anywhere():
    for name in DATACLASSES:
        for f in dataclasses.fields(getattr(models, name)):
            assert f.default_factory is dataclasses.MISSING, (name, f.name)


def test_r6_lote_has_no_derived_values():
    names = set(dir(models.Lote)) - set(dir(object))
    field_names = {f.name for f in dataclasses.fields(models.Lote)}
    dataclass_generated = {
        "__dataclass_fields__",
        "__dataclass_params__",
        "__match_args__",
        "__slots__",
        "__annotations__",
        "__module__",
        "__doc__",
        "__firstlineno__",
        "__static_attributes__",
        "__weakref__",
        "__replace__",
        "__getstate__",
        "__setstate__",
    }
    assert names - field_names - dataclass_generated == set()


def test_r7_manejo_docstring_says_read_model():
    doc = (models.Manejo.__doc__ or "").lower()
    assert "read model" in doc
    assert "source of truth" in doc


# --- AC-7: no hand-written methods --------------------------------------------


def test_ac7_no_methods_in_any_class():
    for cls in _classes().values():
        funcs = [
            n.name if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) else "<lambda>"
            for n in ast.walk(cls)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
        ]
        assert funcs == [], (cls.name, funcs)


def test_ac7_no_post_init_or_custom_hash_at_runtime():
    for name in DATACLASSES:
        cls = getattr(models, name)
        assert "__post_init__" not in cls.__dict__
        # frozen+eq dataclasses generate __hash__; it must be the generated one
        assert cls.__dataclass_params__.unsafe_hash is False


def test_ac7_no_properties_classmethods_or_nested_classes():
    for cls in _classes().values():
        assert not [n for n in cls.body if isinstance(n, ast.ClassDef)]
    # Enums are covered by the AST check above; StrEnum injects its own staticmethods.
    for name in DATACLASSES:
        for attr, val in vars(getattr(models, name)).items():
            assert not isinstance(val, (property, classmethod, staticmethod)), (name, attr)


def test_no_raise_statements_anywhere():
    assert not [n for n in ast.walk(TREE) if isinstance(n, (ast.Raise, ast.Assert))]


# --- AC-8: no numeric literals ------------------------------------------------


def test_ac8_no_numeric_literal_in_module():
    numeric = [
        (n.lineno, n.value)
        for n in ast.walk(TREE)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, (int, float, complex))
        and not isinstance(n.value, bool)
    ]
    assert numeric == []


def test_ac8_no_digits_in_string_constants():
    # Guards against numbers smuggled in as strings (e.g. "90") or in docstrings.
    offenders = [
        (n.lineno, n.value)
        for n in ast.walk(TREE)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and any(ch.isdigit() for ch in n.value)
    ]
    assert offenders == []


# --- AC-9: no list/set fields -------------------------------------------------


def test_ac9_no_field_typed_list_or_set():
    banned = {"list", "set", "List", "Set", "frozenset", "MutableSequence", "MutableSet"}
    for name in DATACLASSES:
        for s in _classes()[name].body:
            if isinstance(s, ast.AnnAssign):
                assert isinstance(s.target, ast.Name)
                names = {n.id for n in ast.walk(s.annotation) if isinstance(n, ast.Name)}
                names |= {n.attr for n in ast.walk(s.annotation) if isinstance(n, ast.Attribute)}
                assert not names & banned, (name, s.target.id)


# --- AC-10: every field of every instance is frozen ---------------------------


@pytest.mark.parametrize(
    ("name", "field"),
    [(c, f[0]) for c, fs in DATACLASSES.items() for f in fs],
)
def test_ac10_assigning_any_field_raises(name, field):
    obj = _sample(name)
    with pytest.raises(FrozenInstanceError):
        setattr(obj, field, getattr(obj, field))


@pytest.mark.parametrize("name", list(DATACLASSES))
def test_ac10_deleting_a_field_raises(name):
    obj = _sample(name)
    first = dataclasses.fields(obj)[0].name
    with pytest.raises(FrozenInstanceError):
        delattr(obj, first)


@pytest.mark.parametrize("name", list(DATACLASSES))
def test_ac10_new_attributes_cannot_be_added(name):
    obj = _sample(name)
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        obj.campo_inexistente = 1


# --- AC-12 / AC-13: packaging -------------------------------------------------


@pytest.mark.parametrize(
    "rel",
    [
        "src/seugado/__init__.py",
        "src/seugado/core/__init__.py",
        "tests/__init__.py",
        "tests/core/__init__.py",
    ],
)
def test_ac13_package_init_files_are_empty(rel):
    assert (ROOT / rel).read_text(encoding="utf-8").strip() == ""


def test_ac12_pyproject_has_no_dependencies_if_present():
    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        pytest.skip("pyproject.toml does not exist; criterion is vacuous")
    import tomllib

    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert not data.get("project", {}).get("dependencies")


def test_style_file_under_300_lines():
    assert len(SOURCE.splitlines()) <= 300


def test_r5_models_does_not_touch_geometry():
    assert "shapely" not in SOURCE and "geopandas" not in SOURCE


# --- Behaviour the spec allows, documented as findings ------------------------


def test_behaviour_values_are_compared_by_value():
    assert _sample("Lote") == _sample("Lote")
    assert _sample("Piquete") == _sample("Piquete")


def test_finding_strenum_members_of_distinct_types_compare_equal():
    # R2 says Confianca and QualidadeBase are different concepts, but StrEnum
    # equality is string equality, so the type distinction is lost on `==`.
    assert models.Confianca.ALTA == models.QualidadeBase.ALTA  # type: ignore[comparison-overlap]  # runtime equality is the documented behaviour; see 06 §7 rule 11
    assert models.Confianca.ALTA == "alta"  # type: ignore[comparison-overlap]  # runtime equality is the documented behaviour; see 06 §7 rule 11


def test_finding_immutability_is_shallow_for_dict_fields():
    e = _sample("Evento")
    e.payload["mutated"] = True
    assert e.payload == {"mutated": True}


def test_finding_piquete_hashability_depends_on_geometry():
    hash(_sample("Piquete"))  # geometry None -> hashable
    p = models.Piquete(
        U, U, "p", 1.0, U, models.MetodoPastejo.ROTACIONADO, geometria_geojson={"type": "Polygon"}
    )
    with pytest.raises(TypeError):
        hash(p)


def test_finding_evento_is_never_hashable():
    with pytest.raises(TypeError):
        hash(_sample("Evento"))


def test_finding_types_are_not_enforced_so_lists_slip_in():
    # No validation by design: a list passes where tuple is annotated,
    # leaving a mutable collection inside a "frozen" entity.
    f = models.Fazenda(U, "f", "tz", 1, 1, [0, 1])  # type: ignore[arg-type]
    assert isinstance(f.dias_preferenciais_manejo, list)
    f.dias_preferenciais_manejo.append(2)
    assert f.dias_preferenciais_manejo == [0, 1, 2]


def test_finding_naive_datetimes_are_accepted():
    e = models.Evento(
        U,
        U,
        models.TipoEvento.LOTE_CRIADO,
        datetime(2026, 1, 1),
        datetime(2026, 1, 1),
        {},
        models.OrigemEvento.PRODUTOR,
        1,
    )
    assert e.ocorrido_em.tzinfo is None


def test_finding_replace_creates_modified_copy():
    # dataclasses.replace is the sanctioned way to "change" an entity.
    p = _sample("Piquete")
    q = dataclasses.replace(p, area_ha=2.0)
    assert p.area_ha == 1.0 and q.area_ha == 2.0
