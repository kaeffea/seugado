"""Independent conformance suite covering SPEC-007 (Eventos MVP).

Written by the tester role (Antigravity), not the implementer.
Tests map to requirements of SPEC-007 and verification scenarios in KIT-ACEITE-007.
"""

import ast
import dataclasses
import enum
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from seugado.core.models import (
    CategoriaAnimal,
    ComposicaoLote,
    Confianca,
    Evento,
    MetodoPastejo,
    OrigemEvento,
    OrigemPeso,
    TipoEvento,
)
from seugado.core.projecao import (
    SituacaoPiquete,
    projetar,
)
from seugado.core.regras import combinar_confianca
from seugado.persistencia import eventos

ROOT = Path(__file__).resolve().parents[2]


# ==============================================================================
# Structural Checks (KIT-ACEITE-007)
# ==============================================================================


def test_origem_peso_enum():
    """OrigemPeso has exactly PRODUTOR='produtor' and UA_TABELA='ua_tabela'."""
    assert issubclass(OrigemPeso, enum.StrEnum)
    assert {m.name: m.value for m in OrigemPeso} == {
        "PRODUTOR": "produtor",
        "UA_TABELA": "ua_tabela",
    }


def test_composicao_lote_origem_peso_field():
    """ComposicaoLote has origem_peso as its last field with default PRODUTOR."""
    fields = dataclasses.fields(ComposicaoLote)
    assert fields[-1].name == "origem_peso"
    assert fields[-1].default == OrigemPeso.PRODUTOR
    assert ComposicaoLote.__slots__ is not None

    # Default constructor works without specifying origem_peso
    c = ComposicaoLote(
        categoria=CategoriaAnimal.ADULTO,
        n_animais=10,
        peso_medio_kg=450.0,
    )
    assert c.origem_peso == OrigemPeso.PRODUTOR


def test_tipo_evento_thirteen_members_altura_medida_last():
    """TipoEvento has 13 members; ALTURA_MEDIDA is the last member."""
    members = list(TipoEvento)
    assert len(members) == 13
    assert members[-1] == TipoEvento.ALTURA_MEDIDA
    assert TipoEvento.ALTURA_MEDIDA.value == "altura_medida"


def test_payload_por_tipo_thirteen_entries_extra_forbid():
    """PAYLOAD_POR_TIPO has 13 entries; all models forbid extra fields."""
    assert len(eventos.PAYLOAD_POR_TIPO) == 13
    assert TipoEvento.ALTURA_MEDIDA in eventos.PAYLOAD_POR_TIPO
    assert eventos.PAYLOAD_POR_TIPO[TipoEvento.ALTURA_MEDIDA] is eventos.PayloadAlturaMedida

    for tipo, model in eventos.PAYLOAD_POR_TIPO.items():
        assert model.model_config.get("extra") == "forbid", f"{tipo} does not forbid extra"


def test_payload_leitura_satelite_fields():
    """PayloadLeituraSatelite has exactly the 9 fields from R3.4; no massa_kg_ms_ha."""
    fields = list(eventos.PayloadLeituraSatelite.model_fields.keys())
    expected = [
        "entidade_id",
        "piquete_id",
        "data",
        "ndvi",
        "refletancia_red",
        "refletancia_nir",
        "origem_ndvi",
        "pct_nuvem",
        "pixels_validos",
    ]
    assert fields == expected
    assert "massa_kg_ms_ha" not in fields


def test_ordem_confianca_dict_and_combinar_confianca():
    """_ORDEM_CONFIANCA exists and combinar_confianca does not compare enum members directly."""
    regras_path = ROOT / "src" / "seugado" / "core" / "regras.py"
    source = regras_path.read_text(encoding="utf-8")
    assert "_ORDEM_CONFIANCA" in source

    # Check that combining empty raises ValueError
    with pytest.raises(ValueError):
        combinar_confianca()

    assert combinar_confianca(Confianca.ALTA, Confianca.MEDIA, Confianca.ALTA) == Confianca.MEDIA
    assert combinar_confianca(Confianca.ALTA) == Confianca.ALTA
    assert combinar_confianca(Confianca.MEDIA, Confianca.BAIXA) == Confianca.BAIXA


def test_core_isolation():
    """core/ does not import from persistencia, sensing, planner, api."""
    forbidden = {"persistencia", "sensing", "planner", "api"}
    for py_file in (ROOT / "src" / "seugado" / "core").glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    assert root_pkg not in forbidden, f"{py_file.name} imports {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                parts = node.module.split(".")
                for part in parts:
                    assert part not in forbidden, f"{py_file.name} from-imports {node.module}"


# ==============================================================================
# Canonical Case (Worked Example in SPEC-007)
# ==============================================================================

SQUARE_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [[0.0, 0.0], [0.0, 0.01], [0.01, 0.01], [0.01, 0.0], [0.0, 0.0]],
    ],
}


def test_canonical_worked_example():
    """Worked example from SPEC-007.

    Events in ocorrido_em order:
    - piquete_criado P1 (square polygon, 4.0 ha)
    - piquete_criado P2
    - lote_criado L1 (40 novilho, 337.5 kg, origem_peso="ua_tabela")
    - manejo_confirmado L1 -> P1 on 2026-09-20
    - altura_medida P2 = 28.0 cm on 2026-09-21
    - manejo_recomendado L1 -> P2 (entidade M1)
    - manejo_divergente (entidade M1, lote_id L1, piquete_real_id P2, data_execucao 2026-09-24)

    State expected:
    - P2 ocupado by L1 since 2026-09-24
    - P1 descansando since 2026-09-24
    - alturas[P2].altura_cm == 28.0
    - L1 composicao has origem_peso == OrigemPeso.UA_TABELA
    """
    fazenda_id = uuid.uuid4()
    p1_id = uuid.uuid4()
    p2_id = uuid.uuid4()
    l1_id = uuid.uuid4()
    cultivar_id = uuid.uuid4()
    m1_id = uuid.uuid4()

    eventos_lista = [
        Evento(
            id=uuid.uuid4(),
            fazenda_id=fazenda_id,
            tipo=TipoEvento.PIQUETE_CRIADO,
            ocorrido_em=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
            registrado_em=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
            payload={
                "entidade_id": p1_id,
                "nome": "P1",
                "area_ha": 4.0,
                "cultivar_id": cultivar_id,
                "metodo_pastejo": MetodoPastejo.ROTACIONADO.value,
                "ativo": True,
                "geometria_geojson": SQUARE_GEOJSON,
            },
            origem=OrigemEvento.PRODUTOR,
            sequencia=1,
        ),
        Evento(
            id=uuid.uuid4(),
            fazenda_id=fazenda_id,
            tipo=TipoEvento.PIQUETE_CRIADO,
            ocorrido_em=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
            registrado_em=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
            payload={
                "entidade_id": p2_id,
                "nome": "P2",
                "area_ha": 5.0,
                "cultivar_id": cultivar_id,
                "metodo_pastejo": MetodoPastejo.ROTACIONADO.value,
                "ativo": True,
                "geometria_geojson": SQUARE_GEOJSON,
            },
            origem=OrigemEvento.PRODUTOR,
            sequencia=2,
        ),
        Evento(
            id=uuid.uuid4(),
            fazenda_id=fazenda_id,
            tipo=TipoEvento.LOTE_CRIADO,
            ocorrido_em=datetime(2026, 9, 3, 8, 0, tzinfo=UTC),
            registrado_em=datetime(2026, 9, 3, 8, 0, tzinfo=UTC),
            payload={
                "entidade_id": l1_id,
                "nome": "L1",
                "composicao": [
                    {
                        "categoria": "novilho",
                        "n_animais": 40,
                        "peso_medio_kg": 337.5,
                        "origem_peso": "ua_tabela",
                    }
                ],
                "indissoluvel": False,
            },
            origem=OrigemEvento.PRODUTOR,
            sequencia=3,
        ),
        Evento(
            id=uuid.uuid4(),
            fazenda_id=fazenda_id,
            tipo=TipoEvento.MANEJO_CONFIRMADO,
            ocorrido_em=datetime(2026, 9, 20, 8, 0, tzinfo=UTC),
            registrado_em=datetime(2026, 9, 20, 8, 0, tzinfo=UTC),
            payload={
                "entidade_id": uuid.uuid4(),
                "lote_id": l1_id,
                "piquete_destino_id": p1_id,
                "data_execucao": "2026-09-20",
            },
            origem=OrigemEvento.PRODUTOR,
            sequencia=4,
        ),
        Evento(
            id=uuid.uuid4(),
            fazenda_id=fazenda_id,
            tipo=TipoEvento.ALTURA_MEDIDA,
            ocorrido_em=datetime(2026, 9, 21, 8, 0, tzinfo=UTC),
            registrado_em=datetime(2026, 9, 21, 8, 0, tzinfo=UTC),
            payload={
                "entidade_id": uuid.uuid4(),
                "piquete_id": p2_id,
                "data": date(2026, 9, 21),
                "altura_cm": 28.0,
                "meio": "bot",
            },
            origem=OrigemEvento.PRODUTOR,
            sequencia=5,
        ),
        Evento(
            id=uuid.uuid4(),
            fazenda_id=fazenda_id,
            tipo=TipoEvento.MANEJO_RECOMENDADO,
            ocorrido_em=datetime(2026, 9, 23, 8, 0, tzinfo=UTC),
            registrado_em=datetime(2026, 9, 23, 8, 0, tzinfo=UTC),
            payload={"entidade_id": m1_id},
            origem=OrigemEvento.SISTEMA,
            sequencia=6,
        ),
        Evento(
            id=uuid.uuid4(),
            fazenda_id=fazenda_id,
            tipo=TipoEvento.MANEJO_DIVERGENTE,
            ocorrido_em=datetime(2026, 9, 24, 8, 0, tzinfo=UTC),
            registrado_em=datetime(2026, 9, 24, 8, 0, tzinfo=UTC),
            payload={
                "entidade_id": m1_id,
                "lote_id": l1_id,
                "piquete_real_id": p2_id,
                "data_execucao": "2026-09-24",
                "motivo": "pasto P2 estava melhor",
            },
            origem=OrigemEvento.PRODUTOR,
            sequencia=7,
        ),
    ]

    estado = projetar(eventos_lista)

    assert estado.piquetes[p2_id].situacao == SituacaoPiquete.OCUPADO
    assert estado.piquetes[p2_id].lote_atual_id == l1_id
    assert estado.piquetes[p2_id].desde == date(2026, 9, 24)

    assert estado.piquetes[p1_id].situacao == SituacaoPiquete.DESCANSANDO
    assert estado.piquetes[p1_id].lote_atual_id is None
    assert estado.piquetes[p1_id].desde == date(2026, 9, 24)

    assert p2_id in estado.alturas
    assert estado.alturas[p2_id].altura_cm == 28.0

    lote = estado.lotes[l1_id]
    assert lote.piquete_atual_id == p2_id
    # check ComposicaoLote item in projecao: peso_vivo_total_kg is 40 * 337.5 = 13500.0
    assert lote.peso_vivo_total_kg == pytest.approx(13500.0)


# ==============================================================================
# Casos que a spec não mostra (KIT-ACEITE-007)
# ==============================================================================


def test_hidden_case_1_combinar_confianca_baixa_alta():
    """Caso 1: combinar_confianca(BAIXA, ALTA) -> BAIXA."""
    assert combinar_confianca(Confianca.BAIXA, Confianca.ALTA) == Confianca.BAIXA


def test_hidden_case_2_altura_medida_latest_date_wins():
    """Caso 2: Duas altura_medida no mesmo piquete, 20/09 (30cm) e 18/09 (25cm).

    Gravadas nessa ordem -> fica 30cm (a mais antiga com data menor não substitui).
    """
    fazenda_id = uuid.uuid4()
    p_id = uuid.uuid4()
    e1 = Evento(
        id=uuid.uuid4(),
        fazenda_id=fazenda_id,
        tipo=TipoEvento.ALTURA_MEDIDA,
        ocorrido_em=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        registrado_em=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        payload={
            "entidade_id": uuid.uuid4(),
            "piquete_id": p_id,
            "data": date(2026, 9, 20),
            "altura_cm": 30.0,
            "meio": "bot",
        },
        origem=OrigemEvento.PRODUTOR,
        sequencia=1,
    )
    e2 = Evento(
        id=uuid.uuid4(),
        fazenda_id=fazenda_id,
        tipo=TipoEvento.ALTURA_MEDIDA,
        ocorrido_em=datetime(2026, 9, 21, 10, 0, tzinfo=UTC),
        registrado_em=datetime(2026, 9, 21, 10, 0, tzinfo=UTC),
        payload={
            "entidade_id": uuid.uuid4(),
            "piquete_id": p_id,
            "data": date(2026, 9, 18),  # older date!
            "altura_cm": 25.0,
            "meio": "bot",
        },
        origem=OrigemEvento.PRODUTOR,
        sequencia=2,
    )
    estado = projetar([e1, e2])
    assert estado.alturas[p_id].altura_cm == 30.0
    assert estado.alturas[p_id].data == date(2026, 9, 20)


def test_hidden_case_3_piquete_alterado_geometria_nova():
    """Caso 3: piquete_alterado com geometria nova -> EstadoPiquete tem a nova."""
    fazenda_id = uuid.uuid4()
    p_id = uuid.uuid4()
    cultivar_id = uuid.uuid4()

    geo_old = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [0.0, 0.0]]],
    }
    geo_new = {
        "type": "Polygon",
        "coordinates": [[[1.0, 1.0], [1.0, 2.0], [2.0, 2.0], [1.0, 1.0]]],
    }

    e1 = Evento(
        id=uuid.uuid4(),
        fazenda_id=fazenda_id,
        tipo=TipoEvento.PIQUETE_CRIADO,
        ocorrido_em=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        registrado_em=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        payload={
            "entidade_id": p_id,
            "nome": "P1",
            "area_ha": 5.0,
            "cultivar_id": cultivar_id,
            "metodo_pastejo": "rotacionado",
            "ativo": True,
            "geometria_geojson": geo_old,
        },
        origem=OrigemEvento.PRODUTOR,
        sequencia=1,
    )
    e2 = Evento(
        id=uuid.uuid4(),
        fazenda_id=fazenda_id,
        tipo=TipoEvento.PIQUETE_ALTERADO,
        ocorrido_em=datetime(2026, 9, 5, 8, 0, tzinfo=UTC),
        registrado_em=datetime(2026, 9, 5, 8, 0, tzinfo=UTC),
        payload={
            "entidade_id": p_id,
            "nome": "P1-Novo",
            "area_ha": 6.0,
            "cultivar_id": cultivar_id,
            "metodo_pastejo": "rotacionado",
            "ativo": True,
            "geometria_geojson": geo_new,
        },
        origem=OrigemEvento.PRODUTOR,
        sequencia=2,
    )

    estado = projetar([e1, e2])
    assert estado.piquetes[p_id].geometria_geojson == geo_new
    assert estado.piquetes[p_id].nome == "P1-Novo"
    assert estado.piquetes[p_id].area_ha == 6.0


def test_hidden_case_4_payload_point_geometry_validation_error():
    """Caso 4: Payload de piquete com Point geometry levanta ValidationError."""
    point_payload = {
        "entidade_id": uuid.uuid4(),
        "nome": "Piquete Ponto",
        "area_ha": 5.0,
        "cultivar_id": uuid.uuid4(),
        "metodo_pastejo": "rotacionado",
        "ativo": True,
        "geometria_geojson": {
            "type": "Point",
            "coordinates": [0.0, 0.0],
        },
    }
    with pytest.raises(ValidationError):
        eventos.PayloadPiqueteCriado.model_validate(point_payload)

    # Coordinates with fewer than 4 positions also raises ValidationError
    triangle_payload = {
        **point_payload,
        "geometria_geojson": {
            "type": "Polygon",
            "coordinates": [[[0.0, 0.0], [0.0, 1.0], [0.0, 0.0]]],
        },
    }
    with pytest.raises(ValidationError):
        eventos.PayloadPiqueteCriado.model_validate(triangle_payload)
