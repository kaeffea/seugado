"""Independent conformance suite covering SPEC-014 (Projected farm state).

Written by the tester role (Antigravity), not the implementer.
Tests map to requirements of SPEC-014 and verification scenarios in KIT-ACEITE-014.
"""

import ast
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import psycopg
import pytest

from seugado.contratos import EstadoProjetado, estado_para_dict
from seugado.core.models import (
    CategoriaAnimal,
    ComposicaoLote,
    Confianca,
    Evento,
    MetodoPastejo,
    OrigemEvento,
    OrigemPeso,
    ParametrosRegime,
    QualidadeBase,
    TipoEvento,
)
from seugado.core.projecao import projetar
from seugado.persistencia.catalogo import CultivarCatalogo
from seugado.persistencia.eventos import registrar_evento
from seugado.planner import carga
from seugado.planner.estado import (
    avancar_massa_um_dia,
    confianca_estimativa,
    consumo_lote,
    projetar_estado,
)
from seugado.sensing.clima import ClimaDia, radiacao_extraterrestre_mj_m2_dia
from seugado.sensing.safer import taxa_acumulo_safer

ROOT = Path(__file__).resolve().parents[2]
ESTADO_PY = ROOT / "src" / "seugado" / "planner" / "estado.py"
ESTADO_UTIL_PY = ROOT / "src" / "seugado" / "planner" / "estado_util.py"
CARGA_PY = ROOT / "src" / "seugado" / "planner" / "carga.py"

FAZENDA_TESTE_ID = UUID("00000000-0000-0000-0000-00000000fa2e")
LAT_FAZENDA = -9.78
LON_FAZENDA = -36.09
ET0_ANUAL = 4.5

MARANDU = CultivarCatalogo(
    id=UUID("00000000-0000-0000-0000-0000000000a1"),
    slug="marandu",
    nome="Marandu",
    parametros_por_regime=(
        ParametrosRegime(
            MetodoPastejo.ROTACIONADO, 30.0, 15.0, None, None, Confianca.ALTA, "fonte"
        ),
        ParametrosRegime(
            MetodoPastejo.CONTINUO, None, None, 35.0, 20.0, Confianca.ALTA, "fonte"
        ),
    ),
    eficiencia_por_metodo=((MetodoPastejo.ROTACIONADO, 0.72),),
    densidade_kg_ha_por_cm=110.0,
    rue_max_g_por_mj=2.31,
    temperatura_base_c=15.0,
    descanso_min_dias=21.0,
    qualidade_base=QualidadeBase.ALTA,
)

MOMBACA = CultivarCatalogo(
    id=UUID("00000000-0000-0000-0000-0000000000a2"),
    slug="mombaca",
    nome="Mombaça",
    parametros_por_regime=(
        ParametrosRegime(
            MetodoPastejo.ROTACIONADO, 85.0, 45.0, None, None, Confianca.MEDIA, "fonte"
        ),
    ),
    eficiencia_por_metodo=((MetodoPastejo.ROTACIONADO, 0.70),),
    densidade_kg_ha_por_cm=None,
    rue_max_g_por_mj=None,
    temperatura_base_c=None,
    descanso_min_dias=28.0,
    qualidade_base=None,
)

CATALOGO = {MARANDU.id: MARANDU, MOMBACA.id: MOMBACA}


def _criar_clima(
    inicio: date, fim: date, pulo: set[date] | None = None, rg: float = 20.0, t_med: float = 25.0
) -> list[ClimaDia]:
    """Build consecutive ClimaDia sequence."""
    dias: list[ClimaDia] = []
    curr = inicio
    pular = pulo or set()
    while curr <= fim:
        if curr not in pular:
            dias.append(
                ClimaDia(
                    data=curr,
                    rg_mj_m2_dia=rg,
                    t_max_c=t_med + 5.0,
                    t_min_c=t_med - 5.0,
                    t_media_c=t_med,
                    et0_mm_dia=4.0,
                    chuva_mm=0.0,
                    previsto=False,
                )
            )
        curr += timedelta(days=1)
    return dias


class EventLogBuilder:
    """Helper to assemble an in-memory sequence of Evento objects."""

    def __init__(self, fazenda_id: UUID = FAZENDA_TESTE_ID) -> None:
        self.fazenda_id = fazenda_id
        self.eventos: list[Evento] = []

    def adicionar(
        self,
        tipo: TipoEvento,
        data_evento: date,
        origem: OrigemEvento = OrigemEvento.PRODUTOR,
        **payload: Any,
    ) -> UUID:
        entidade_id = payload.setdefault("entidade_id", str(uuid4()))
        ts = datetime(data_evento.year, data_evento.month, data_evento.day, 12, 0, tzinfo=UTC)
        seq = len(self.eventos) + 1
        ev = Evento(
            id=uuid4(),
            fazenda_id=self.fazenda_id,
            tipo=tipo,
            ocorrido_em=ts,
            registrado_em=ts,
            payload=payload,
            origem=origem,
            sequencia=seq,
        )
        self.eventos.append(ev)
        return UUID(entidade_id)

    def criar_piquete(
        self,
        nome: str,
        cultivar: CultivarCatalogo,
        area_ha: float = 2.0,
        metodo: str = "rotacionado",
    ) -> UUID:
        return self.adicionar(
            TipoEvento.PIQUETE_CRIADO,
            date(2026, 1, 1),
            nome=nome,
            area_ha=area_ha,
            cultivar_id=str(cultivar.id),
            metodo_pastejo=metodo,
            ativo=True,
            geometria_geojson={"type": "Polygon", "coordinates": []},
        )

    def medir_altura(self, piquete_id: UUID, dia: date, altura_cm: float) -> None:
        self.adicionar(
            TipoEvento.ALTURA_MEDIDA,
            dia,
            piquete_id=str(piquete_id),
            data=dia.isoformat(),
            altura_cm=altura_cm,
            meio="regua",
        )

    def ler_satelite(
        self,
        piquete_id: UUID,
        dia: date,
        ndvi: float = 0.75,
        red: float = 0.04,
        nir: float = 0.35,
        pixels: int = 40,
        nuvem: float = 0.0,
    ) -> None:
        self.adicionar(
            TipoEvento.LEITURA_SATELITE,
            dia,
            OrigemEvento.SATELITE,
            piquete_id=str(piquete_id),
            data=dia.isoformat(),
            ndvi=ndvi,
            refletancia_red=red,
            refletancia_nir=nir,
            origem_ndvi="s2",
            pct_nuvem=nuvem,
            pixels_validos=pixels,
        )

    def criar_lote(
        self,
        nome: str,
        n_animais: int = 150,
        peso_medio: float = 337.5,
        categoria: str = "novilho",
        origem_peso: str = "ua_tabela",
    ) -> UUID:
        return self.adicionar(
            TipoEvento.LOTE_CRIADO,
            date(2026, 1, 1),
            nome=nome,
            composicao=[
                {
                    "categoria": categoria,
                    "n_animais": n_animais,
                    "peso_medio_kg": peso_medio,
                    "origem_peso": origem_peso,
                }
            ],
            indissoluvel=False,
        )

    def mover_lote(
        self,
        lote_id: UUID,
        piquete_id: UUID,
        dia: date,
        origem: OrigemEvento = OrigemEvento.PRODUTOR,
    ) -> None:
        self.adicionar(
            TipoEvento.MANEJO_CONFIRMADO,
            dia,
            origem,
            lote_id=str(lote_id),
            piquete_destino_id=str(piquete_id),
            data_execucao=dia.isoformat(),
        )


# ==============================================================================
# 1. Structural Checks (KIT-ACEITE-014)
# ==============================================================================


def test_estado_py_and_util_no_forbidden_imports() -> None:
    """estado.py and estado_util.py must not import psycopg, httpx, or ee directly."""
    for path in (ESTADO_PY, ESTADO_UTIL_PY):
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        forbidden = ("psycopg", "httpx", "ee")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(
                        alias.name == f or alias.name.startswith(f"{f}.") for f in forbidden
                    ), f"Forbidden import in {path.name}: {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not any(
                    node.module == f or node.module.startswith(f"{f}.") for f in forbidden
                ), f"Forbidden import from in {path.name}: {node.module}"


def test_carga_py_no_commit() -> None:
    """carga.py must be strictly read-only and never call .commit()."""
    content = CARGA_PY.read_text(encoding="utf-8")
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "commit"
        ):
            pytest.fail("carga.py calls .commit(), violating read-only spec requirement")


def test_faltantes_no_duplicates_and_insertion_order() -> None:
    """faltantes must have no duplicates and preserve exact specification order."""
    cultivar_incompleto = CultivarCatalogo(
        id=UUID("00000000-0000-0000-0000-0000000000a3"),
        slug="incompleto",
        nome="Incompleto",
        parametros_por_regime=(
            ParametrosRegime(
                MetodoPastejo.ROTACIONADO, None, 15.0, None, None, Confianca.BAIXA, "fonte"
            ),
        ),
        eficiencia_por_metodo=((MetodoPastejo.ROTACIONADO, 0.70),),
        densidade_kg_ha_por_cm=None,
        rue_max_g_por_mj=None,
        temperatura_base_c=None,
        descanso_min_dias=21.0,
        qualidade_base=None,
    )
    catalogo_local = {**CATALOGO, cultivar_incompleto.id: cultivar_incompleto}

    builder = EventLogBuilder()
    data_base = date(2026, 9, 20)
    p_id = builder.criar_piquete("P1", cultivar_incompleto)

    estado_fazenda = projetar(builder.eventos)
    clima = _criar_clima(data_base - timedelta(days=35), data_base + timedelta(days=14))
    centroides = {p_id: (LAT_FAZENDA, LON_FAZENDA)}

    proj = projetar_estado(
        estado_fazenda,
        builder.eventos,
        catalogo_local,
        centroides,
        clima,
        ET0_ANUAL,
        LAT_FAZENDA,
        data_base,
    )
    piq = proj.piquetes[0]
    assert len(piq.faltantes) == len(set(piq.faltantes)), "faltantes contains duplicates"
    indices = {item: idx for idx, item in enumerate(piq.faltantes)}
    assert indices["altura_entrada_cm"] < indices["densidade_kg_ha_por_cm"]
    assert indices["densidade_kg_ha_por_cm"] < indices["altura_inicial"]
    assert indices["altura_inicial"] < indices["imagem_satelite"]


# ==============================================================================
# 2. Canonical Cases (KIT-ACEITE-014 & SPEC-014)
# ==============================================================================


def test_canonical_worked_examples_auxiliares() -> None:
    """Canonical worked examples: 2038.04, 1113.75, and confidence by ruler."""
    assert avancar_massa_um_dia(2420.0, 60.0, 1113.75, 3.5, 0.72) == pytest.approx(
        2038.04, abs=0.01
    )

    comp = (ComposicaoLote(CategoriaAnimal.NOVILHO, 150, 337.5, OrigemPeso.UA_TABELA),)
    assert consumo_lote(comp) == pytest.approx(1113.75)

    nivel, frase = confianca_estimativa(3, 40, 20, False)
    assert nivel == Confianca.MEDIA
    assert frase == "última medição de altura há 20 dias"


def test_canonical_worked_example_projetar_estado() -> None:
    """Marandu measured at 30 cm on data_base gives 3300 kg/ha mass and 14 forecast rates."""
    data_base = date(2026, 9, 21)
    builder = EventLogBuilder()
    p_id = builder.criar_piquete("P1", MARANDU, area_ha=3.5)
    builder.medir_altura(p_id, data_base, 30.0)
    builder.ler_satelite(p_id, data_base, ndvi=0.75, red=0.04, nir=0.35, pixels=40)

    estado_fazenda = projetar(builder.eventos)
    clima = _criar_clima(data_base, data_base + timedelta(days=14))
    centroides = {p_id: (LAT_FAZENDA, LON_FAZENDA)}

    proj = projetar_estado(
        estado_fazenda,
        builder.eventos,
        CATALOGO,
        centroides,
        clima,
        ET0_ANUAL,
        LAT_FAZENDA,
        data_base,
    )
    piq = proj.piquetes[0]
    assert piq.massa_hoje_kg_ms_ha == pytest.approx(3300.0)
    assert piq.altura_hoje_cm == pytest.approx(30.0)
    assert len(piq.taxa_acumulo_prevista_kg_ms_ha_dia) == 14

    for i, taxa in enumerate(piq.taxa_acumulo_prevista_kg_ms_ha_dia):
        c_dia = clima[i]
        esperada = taxa_acumulo_safer(
            0.75,
            0.04,
            0.35,
            c_dia.rg_mj_m2_dia,
            c_dia.t_media_c,
            radiacao_extraterrestre_mj_m2_dia(LAT_FAZENDA, c_dia.data),
            ET0_ANUAL,
            MARANDU.rue_max_g_por_mj or 2.31,
        ).taxa_acumulo_kg_ms_ha_dia
        assert taxa == pytest.approx(esperada, abs=1e-4)


# ==============================================================================
# 3. Hidden Cases (KIT-ACEITE-014)
# ==============================================================================


def test_hidden_case_1_avancar_massa_sem_consumo() -> None:
    """Caso 1: avancar_massa_um_dia(2000, 50, 0, 4, None) -> 2050."""
    res = avancar_massa_um_dia(2000.0, 50.0, 0.0, 4.0, None)
    assert res == pytest.approx(2050.0)


def test_hidden_case_2_confianca_estimativa_sem_imagem() -> None:
    """Caso 2: confianca_estimativa(None, None, 50, True) -> (BAIXA, sem imagem satelite)."""
    nivel, frase = confianca_estimativa(None, None, 50, True)
    assert nivel == Confianca.BAIXA
    assert frase == "nenhuma imagem de satélite sem nuvem nos últimos 30 dias"


def test_hidden_case_3_marandu_sem_lote_dois_dias() -> None:
    """Caso 3: Marandu medido a 25 cm 2 dias antes de data_base, sem lote:

    massa_hoje = 2750 + taxa(d1) + taxa(d2).
    """
    data_base = date(2026, 9, 20)
    d1 = data_base - timedelta(days=2)
    d2 = data_base - timedelta(days=1)

    builder = EventLogBuilder()
    p_id = builder.criar_piquete("P1", MARANDU, area_ha=2.0)
    builder.medir_altura(p_id, d1, 25.0)
    builder.ler_satelite(p_id, d1, ndvi=0.70, red=0.05, nir=0.30, pixels=30)

    clima = _criar_clima(d1, data_base + timedelta(days=14), rg=22.0, t_med=26.0)
    estado_fazenda = projetar(builder.eventos)
    centroides = {p_id: (LAT_FAZENDA, LON_FAZENDA)}

    rue = MARANDU.rue_max_g_por_mj or 2.31
    clima_dict = {c.data: c for c in clima}
    taxa_d1 = taxa_acumulo_safer(
        0.70,
        0.05,
        0.30,
        clima_dict[d1].rg_mj_m2_dia,
        clima_dict[d1].t_media_c,
        radiacao_extraterrestre_mj_m2_dia(LAT_FAZENDA, d1),
        ET0_ANUAL,
        rue,
    ).taxa_acumulo_kg_ms_ha_dia

    taxa_d2 = taxa_acumulo_safer(
        0.70,
        0.05,
        0.30,
        clima_dict[d2].rg_mj_m2_dia,
        clima_dict[d2].t_media_c,
        radiacao_extraterrestre_mj_m2_dia(LAT_FAZENDA, d2),
        ET0_ANUAL,
        rue,
    ).taxa_acumulo_kg_ms_ha_dia

    massa_esperada = 2750.0 + taxa_d1 + taxa_d2

    proj = projetar_estado(
        estado_fazenda,
        builder.eventos,
        CATALOGO,
        centroides,
        clima,
        ET0_ANUAL,
        LAT_FAZENDA,
        data_base,
    )
    piq = proj.piquetes[0]
    assert piq.massa_hoje_kg_ms_ha is not None
    assert piq.massa_hoje_kg_ms_ha == pytest.approx(massa_esperada, abs=0.01)


def test_hidden_case_4_marandu_ocupado_com_lote_dois_dias() -> None:
    """Caso 4: Piquete com lote de 1000 kg/dia, eficiencia 0.72, 2 ha -> subtrai 694.44/dia."""
    subtracao_dia = 1000.0 / (0.72 * 2.0)
    assert subtracao_dia == pytest.approx(694.44, abs=0.01)

    data_base = date(2026, 9, 20)
    d1 = data_base - timedelta(days=2)
    d2 = data_base - timedelta(days=1)

    builder = EventLogBuilder()
    p_id = builder.criar_piquete("P1", MARANDU, area_ha=2.0)
    builder.medir_altura(p_id, d1, 25.0)
    builder.ler_satelite(p_id, d1, ndvi=0.70, red=0.05, nir=0.30, pixels=30)

    peso_novilho = 1000.0 / (100 * 0.022)
    lote_id = builder.criar_lote(
        "Lote 1", n_animais=100, peso_medio=peso_novilho, categoria="novilho"
    )
    builder.mover_lote(lote_id, p_id, d1)

    clima = _criar_clima(d1, data_base + timedelta(days=14), rg=22.0, t_med=26.0)
    estado_fazenda = projetar(builder.eventos)
    centroides = {p_id: (LAT_FAZENDA, LON_FAZENDA)}

    rue = MARANDU.rue_max_g_por_mj or 2.31
    clima_dict = {c.data: c for c in clima}
    taxa_d1 = taxa_acumulo_safer(
        0.70,
        0.05,
        0.30,
        clima_dict[d1].rg_mj_m2_dia,
        clima_dict[d1].t_media_c,
        radiacao_extraterrestre_mj_m2_dia(LAT_FAZENDA, d1),
        ET0_ANUAL,
        rue,
    ).taxa_acumulo_kg_ms_ha_dia
    taxa_d2 = taxa_acumulo_safer(
        0.70,
        0.05,
        0.30,
        clima_dict[d2].rg_mj_m2_dia,
        clima_dict[d2].t_media_c,
        radiacao_extraterrestre_mj_m2_dia(LAT_FAZENDA, d2),
        ET0_ANUAL,
        rue,
    ).taxa_acumulo_kg_ms_ha_dia

    massa_esperada = (2750.0 + taxa_d1 - subtracao_dia) + taxa_d2 - subtracao_dia

    proj = projetar_estado(
        estado_fazenda,
        builder.eventos,
        CATALOGO,
        centroides,
        clima,
        ET0_ANUAL,
        LAT_FAZENDA,
        data_base,
    )
    piq = proj.piquetes[0]
    assert piq.massa_hoje_kg_ms_ha is not None
    assert piq.massa_hoje_kg_ms_ha == pytest.approx(massa_esperada, abs=0.02)


# ==============================================================================
# 4. Acceptance Scenarios & Edge Cases (SPEC-014)
# ==============================================================================


def test_piquete_sem_regua_rejeita_estimativa() -> None:
    """Paddock without ruler measurement gets 'altura_inicial', None mass, and BAIXA confidence."""
    data_base = date(2026, 9, 20)
    builder = EventLogBuilder()
    p_id = builder.criar_piquete("P1", MARANDU)
    builder.ler_satelite(p_id, data_base)

    estado_fazenda = projetar(builder.eventos)
    clima = _criar_clima(data_base, data_base + timedelta(days=14))
    centroides = {p_id: (LAT_FAZENDA, LON_FAZENDA)}

    proj = projetar_estado(
        estado_fazenda,
        builder.eventos,
        CATALOGO,
        centroides,
        clima,
        ET0_ANUAL,
        LAT_FAZENDA,
        data_base,
    )
    piq = proj.piquetes[0]
    assert "altura_inicial" in piq.faltantes
    assert piq.massa_hoje_kg_ms_ha is None
    assert piq.altura_hoje_cm is None
    assert piq.confianca == Confianca.BAIXA
    assert piq.motivo_confianca == (
        "nenhuma medição de altura com régua registrada para este piquete"
    )


def test_piquete_mombaca_sem_densidade_no_catalogo() -> None:
    """Mombaça paddock (no density) is in projected state with None mass and BAIXA confidence."""
    data_base = date(2026, 9, 20)
    builder = EventLogBuilder()
    p_id = builder.criar_piquete("P1", MOMBACA)
    builder.medir_altura(p_id, data_base, 80.0)
    builder.ler_satelite(p_id, data_base)

    estado_fazenda = projetar(builder.eventos)
    clima = _criar_clima(data_base, data_base + timedelta(days=14))
    centroides = {p_id: (LAT_FAZENDA, LON_FAZENDA)}

    proj = projetar_estado(
        estado_fazenda,
        builder.eventos,
        CATALOGO,
        centroides,
        clima,
        ET0_ANUAL,
        LAT_FAZENDA,
        data_base,
    )
    piq = proj.piquetes[0]
    assert piq.massa_hoje_kg_ms_ha is None
    assert "densidade_kg_ha_por_cm" in piq.faltantes
    assert piq.confianca == Confianca.BAIXA
    assert piq.motivo_confianca == "a cultivar Mombaça ainda não tem calibração no SeuGado"


def test_piquete_imagem_satelite_mais_antiga_que_30_dias() -> None:
    """Satellite image older than 30 days yields 'imagem_satelite' in faltantes."""
    data_base = date(2026, 9, 20)
    d_sat = data_base - timedelta(days=31)

    builder = EventLogBuilder()
    p_id = builder.criar_piquete("P1", MARANDU)
    builder.medir_altura(p_id, data_base, 30.0)
    builder.ler_satelite(p_id, d_sat)

    estado_fazenda = projetar(builder.eventos)
    clima = _criar_clima(data_base, data_base + timedelta(days=14))
    centroides = {p_id: (LAT_FAZENDA, LON_FAZENDA)}

    proj = projetar_estado(
        estado_fazenda,
        builder.eventos,
        CATALOGO,
        centroides,
        clima,
        ET0_ANUAL,
        LAT_FAZENDA,
        data_base,
    )
    piq = proj.piquetes[0]
    assert "imagem_satelite" in piq.faltantes
    assert piq.massa_hoje_kg_ms_ha is None
    assert piq.confianca == Confianca.BAIXA
    assert piq.motivo_confianca == "nenhuma imagem de satélite sem nuvem nos últimos 30 dias"


def test_piquete_clima_faltante_interrompe_estimativa() -> None:
    """Missing ClimaDia for any needed day adds 'clima' and clears forecast."""
    data_base = date(2026, 9, 20)
    builder = EventLogBuilder()
    p_id = builder.criar_piquete("P1", MARANDU)
    builder.medir_altura(p_id, data_base - timedelta(days=2), 30.0)
    builder.ler_satelite(p_id, data_base)

    clima = _criar_clima(
        data_base - timedelta(days=2),
        data_base + timedelta(days=14),
        pulo={data_base - timedelta(days=1)},
    )
    estado_fazenda = projetar(builder.eventos)
    centroides = {p_id: (LAT_FAZENDA, LON_FAZENDA)}

    proj = projetar_estado(
        estado_fazenda,
        builder.eventos,
        CATALOGO,
        centroides,
        clima,
        ET0_ANUAL,
        LAT_FAZENDA,
        data_base,
    )
    piq = proj.piquetes[0]
    assert "clima" in piq.faltantes
    assert piq.massa_hoje_kg_ms_ha is None
    assert piq.taxa_acumulo_prevista_kg_ms_ha_dia == ()
    assert piq.confianca == Confianca.BAIXA
    assert piq.motivo_confianca == "faltam dados de clima para o período"


def test_piquete_estimativa_invalida_safer_fora_da_faixa() -> None:
    """When SAFER calculation fails / raises, 'estimativa_invalida' is recorded."""
    data_base = date(2026, 9, 20)
    builder = EventLogBuilder()
    p_id = builder.criar_piquete("P1", MARANDU)
    builder.medir_altura(p_id, data_base, 30.0)
    builder.ler_satelite(p_id, data_base)

    clima = _criar_clima(data_base, data_base + timedelta(days=14), rg=50.0, t_med=40.0)
    estado_fazenda = projetar(builder.eventos)
    centroides = {p_id: (LAT_FAZENDA, LON_FAZENDA)}

    proj = projetar_estado(
        estado_fazenda,
        builder.eventos,
        CATALOGO,
        centroides,
        clima,
        ET0_ANUAL,
        LAT_FAZENDA,
        data_base,
    )
    piq = proj.piquetes[0]
    assert "estimativa_invalida" in piq.faltantes
    assert piq.massa_hoje_kg_ms_ha is None
    assert piq.confianca == Confianca.BAIXA
    assert piq.motivo_confianca == "o cálculo por satélite saiu da faixa esperada"


def test_lotes_ordenados_e_consumos() -> None:
    """Lotes in EstadoProjetado are sorted by name with accurate intake and confidence."""
    builder = EventLogBuilder()
    builder.criar_lote(
        "Lote B", n_animais=50, peso_medio=400.0, categoria="boi", origem_peso="produtor"
    )
    builder.criar_lote(
        "Lote A", n_animais=100, peso_medio=337.5, categoria="novilho", origem_peso="ua_tabela"
    )

    estado_fazenda = projetar(builder.eventos)
    data_base = date(2026, 9, 20)
    clima = _criar_clima(data_base, data_base + timedelta(days=14))

    proj = projetar_estado(
        estado_fazenda,
        builder.eventos,
        CATALOGO,
        {},
        clima,
        ET0_ANUAL,
        LAT_FAZENDA,
        data_base,
    )
    assert len(proj.lotes) == 2
    assert [lt.nome for lt in proj.lotes] == ["Lote A", "Lote B"]
    assert proj.lotes[0].confianca_peso == Confianca.MEDIA
    assert proj.lotes[1].confianca_peso == Confianca.ALTA


# ==============================================================================
# 5. Carga & Serialização (SPEC-014 / Supabase)
# ==============================================================================


def test_montar_estado_projetado_fazenda_vazia() -> None:
    """montar_estado_projetado on a farm with no events returns an empty EstadoProjetado."""
    conn = MagicMock(spec=psycopg.Connection)
    with patch("seugado.planner.carga.carregar_eventos", return_value=[]):
        proj = carga.montar_estado_projetado(conn, uuid4(), date(2026, 9, 20))
        assert isinstance(proj, EstadoProjetado)
        assert len(proj.piquetes) == 0
        assert len(proj.lotes) == 0
        conn.commit.assert_not_called()


def test_montar_estado_projetado_com_banco_real_e_serializacao() -> None:
    """montar_estado_projetado works against the real Supabase database and serializes to dict."""
    db_url = os.environ.get("SEUGADO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        pytest.skip("No database URL available for live Supabase integration test")

    fazenda_id = uuid4()
    p_id = uuid4()
    data_base = date(2026, 9, 20)

    with psycopg.connect(db_url) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO fazenda (id, nome, timezone, funcionarios_disponiveis,"
                    " animais_por_funcionario_dia) VALUES (%s, 'Fazenda Live Test',"
                    " 'America/Maceio', 1, 100)",
                    (fazenda_id,),
                )
                cur.execute("SELECT id FROM cultivar LIMIT 1")
                row_c = cur.fetchone()
                assert row_c is not None
                cultivar_id = row_c[0]
                poly_geojson = {
                    "type": "Polygon",
                    "coordinates": [[
                        [-36.0900, -9.7800],
                        [-36.0897, -9.7800],
                        [-36.0897, -9.7803],
                        [-36.0900, -9.7803],
                        [-36.0900, -9.7800],
                    ]],
                }
                cur.execute(
                    "INSERT INTO estado_piquete (piquete_id, fazenda_id, cultivar_id,"
                    " nome, area_ha, metodo_pastejo, ativo, geometria, situacao,"
                    " desde, dias_descanso, derivado_ate_sequencia)"
                    " VALUES (%s, %s, %s, 'P1', 0.1, 'rotacionado', true,"
                    " ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 'descansando', %s, 0, 0)",
                    (p_id, fazenda_id, cultivar_id, str(poly_geojson).replace("'", '"'), data_base),
                )
                registrar_evento(
                    conn,
                    fazenda_id,
                    TipoEvento.PIQUETE_CRIADO,
                    OrigemEvento.PRODUTOR,
                    ocorrido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
                    payload={
                        "entidade_id": str(p_id),
                        "nome": "P1",
                        "area_ha": 0.1,
                        "cultivar_id": str(cultivar_id),
                        "metodo_pastejo": "rotacionado",
                        "ativo": True,
                        "geometria_geojson": poly_geojson,
                    },
                )

            # 2. Call montar_estado_projetado with real DB and weather mock
            clima_mock = _criar_clima(
                data_base - timedelta(days=15), data_base + timedelta(days=15)
            )
            with (
                patch("seugado.planner.carga.buscar_clima", return_value=clima_mock),
                patch("seugado.planner.carga.et0_media_anual_mm_dia", return_value=ET0_ANUAL),
            ):
                proj = carga.montar_estado_projetado(conn, fazenda_id, data_base)
                assert isinstance(proj, EstadoProjetado)
                assert len(proj.piquetes) == 1
                assert proj.piquetes[0].nome == "P1"

                d = estado_para_dict(proj)
                assert isinstance(d, dict)
                assert d["fazenda_id"] == str(fazenda_id)
                assert d["data_base"] == data_base.isoformat()
                assert len(d["piquetes"]) == 1
                assert d["piquetes"][0]["nome"] == "P1"

        finally:
            conn.rollback()
