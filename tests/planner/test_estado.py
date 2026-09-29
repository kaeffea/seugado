"""Smoke checks for the planner estado helpers."""

import ast
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

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
from seugado.core.projecao import SituacaoPiquete, projetar
from seugado.persistencia.catalogo import CultivarCatalogo
from seugado.planner import carga
from seugado.planner.estado import (
    avancar_massa_um_dia,
    confianca_estimativa,
    confianca_peso,
    consumo_lote,
    peso_por_ua_kg,
    projetar_estado,
)
from seugado.sensing.clima import ClimaDia, radiacao_extraterrestre_mj_m2_dia
from seugado.sensing.safer import taxa_acumulo_safer


def test_peso_por_ua_kg_novilho() -> None:
    assert peso_por_ua_kg(CategoriaAnimal.NOVILHO) == pytest.approx(337.5)


def test_peso_por_ua_kg_new_categories() -> None:
    assert peso_por_ua_kg(CategoriaAnimal.TOURO) == pytest.approx(562.5)
    assert peso_por_ua_kg(CategoriaAnimal.NOVILHA) == pytest.approx(337.5)


def test_consumo_lote_worked_example() -> None:
    composicao = (ComposicaoLote(CategoriaAnimal.NOVILHO, 150, 337.5, OrigemPeso.UA_TABELA),)
    assert consumo_lote(composicao) == pytest.approx(1113.75)


def test_avancar_massa_um_dia_worked_example() -> None:
    assert avancar_massa_um_dia(2420.0, 60.0, 1113.75, 3.5, 0.72) == pytest.approx(
        2038.04, abs=0.01
    )


def test_avancar_massa_um_dia_sem_consumo() -> None:
    assert avancar_massa_um_dia(2000.0, 50.0, 0.0, 3.0, None) == pytest.approx(2050.0)


def test_avancar_massa_um_dia_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        avancar_massa_um_dia(2000.0, 50.0, 100.0, 0.0, 0.7)
    with pytest.raises(ValueError):
        avancar_massa_um_dia(2000.0, 50.0, 100.0, 3.0, None)
    with pytest.raises(ValueError):
        avancar_massa_um_dia(2000.0, 50.0, 100.0, 3.0, 0.0)


def test_confianca_peso() -> None:
    informado = (ComposicaoLote(CategoriaAnimal.VACA, 10, 450.0, OrigemPeso.PRODUTOR),)
    assert confianca_peso(informado) == (Confianca.ALTA, "peso médio informado por você")
    estimado = (ComposicaoLote(CategoriaAnimal.NOVILHO, 150, 337.5, OrigemPeso.UA_TABELA),)
    assert confianca_peso(estimado) == (
        Confianca.MEDIA,
        "peso médio estimado pela tabela de Unidade Animal",
    )


def test_confianca_estimativa_worked_example() -> None:
    assert confianca_estimativa(3, 40, 20, False) == (
        Confianca.MEDIA,
        "última medição de altura há 20 dias",
    )


def test_confianca_estimativa_sem_imagem() -> None:
    nivel, frase = confianca_estimativa(None, None, 5, False)
    assert nivel == Confianca.BAIXA
    assert frase == "nenhuma imagem de satélite sem nuvem nos últimos 30 dias"


# --- projetar_estado (R3) ----------------------------------------------------------------

FAZENDA = UUID("00000000-0000-0000-0000-00000000fa2e")
DATA_BASE = date(2026, 9, 21)
LAT = -20.0
ET0_ANUAL = 4.5
NDVI, RED, NIR = 0.75, 0.04, 0.35
CALIBRADO = Confianca.ALTA

MARANDU = CultivarCatalogo(
    id=UUID("00000000-0000-0000-0000-0000000000a1"),
    slug="marandu",
    nome="Marandu",
    parametros_por_regime=(
        ParametrosRegime(MetodoPastejo.ROTACIONADO, 25.0, 15.0, None, None, CALIBRADO, "t"),
        ParametrosRegime(MetodoPastejo.CONTINUO, None, None, 40.0, 20.0, CALIBRADO, "t"),
    ),
    eficiencia_por_metodo=((MetodoPastejo.ROTACIONADO, 0.72),),
    densidade_kg_ha_por_cm=110.0,
    rue_max_g_por_mj=1.6,
    temperatura_base_c=15.0,
    descanso_min_dias=21.0,
    qualidade_base=QualidadeBase.MEDIA,
)
MOMBACA = CultivarCatalogo(
    id=UUID("00000000-0000-0000-0000-0000000000a2"),
    slug="mombaca",
    nome="Mombaça",
    parametros_por_regime=(
        ParametrosRegime(MetodoPastejo.ROTACIONADO, 90.0, 45.0, None, None, CALIBRADO, "t"),
    ),
    eficiencia_por_metodo=((MetodoPastejo.ROTACIONADO, 0.7),),
    densidade_kg_ha_por_cm=None,
    rue_max_g_por_mj=1.6,
    temperatura_base_c=15.0,
    descanso_min_dias=30.0,
    qualidade_base=QualidadeBase.ALTA,
)
CATALOGO = {MARANDU.id: MARANDU, MOMBACA.id: MOMBACA}


class _Log:
    """Literal event log builder; sequencia follows insertion order."""

    def __init__(self) -> None:
        self.eventos: list[Evento] = []

    def add(
        self,
        tipo: TipoEvento,
        dia: date,
        origem: OrigemEvento = OrigemEvento.PRODUTOR,
        **payload: Any,
    ) -> UUID:
        entidade_id = payload.setdefault("entidade_id", str(uuid4()))
        quando = datetime(dia.year, dia.month, dia.day, 12, tzinfo=UTC)
        seq = len(self.eventos) + 1
        self.eventos.append(Evento(uuid4(), FAZENDA, tipo, quando, quando, payload, origem, seq))
        return UUID(entidade_id)

    def piquete(self, nome: str, cultivar: CultivarCatalogo, **extra: Any) -> UUID:
        payload: dict[str, Any] = {
            "nome": nome,
            "area_ha": 3.5,
            "cultivar_id": str(cultivar.id),
            "metodo_pastejo": "rotacionado",
            "ativo": True,
            "geometria_geojson": {},
        } | extra
        return self.add(TipoEvento.PIQUETE_CRIADO, date(2026, 1, 1), **payload)

    def altura(self, piquete_id: UUID, dia: date, altura_cm: float) -> None:
        self.add(
            TipoEvento.ALTURA_MEDIDA,
            dia,
            piquete_id=str(piquete_id),
            data=dia.isoformat(),
            altura_cm=altura_cm,
            meio="regua",
        )

    def leitura(self, piquete_id: UUID, dia: date, pixels: int = 40) -> None:
        self.add(
            TipoEvento.LEITURA_SATELITE,
            dia,
            OrigemEvento.SATELITE,
            piquete_id=str(piquete_id),
            data=dia.isoformat(),
            ndvi=NDVI,
            refletancia_red=RED,
            refletancia_nir=NIR,
            origem_ndvi="s2",
            pct_nuvem=0.0,
            pixels_validos=pixels,
        )

    def lote(self) -> UUID:
        item = {
            "categoria": "novilho",
            "n_animais": 150,
            "peso_medio_kg": 337.5,
            "origem_peso": "ua_tabela",
        }
        return self.add(
            TipoEvento.LOTE_CRIADO,
            date(2026, 1, 1),
            nome="Recria",
            composicao=[item],
            indissoluvel=False,
        )

    def entrada(self, lote_id: UUID, piquete_id: UUID, dia: date, origem: OrigemEvento) -> None:
        self.add(
            TipoEvento.MANEJO_CONFIRMADO,
            dia,
            origem,
            lote_id=str(lote_id),
            piquete_destino_id=str(piquete_id),
            data_execucao=dia.isoformat(),
        )


def _clima(inicio: date, fim: date, pular: date | None = None) -> list[ClimaDia]:
    dias = []
    d = inicio
    while d <= fim:
        if d != pular:
            dias.append(ClimaDia(d, 20.0, 30.0, 18.0, 24.0, 4.5, 0.0, d > DATA_BASE))
        d += timedelta(days=1)
    return dias


def _taxa(dia: date) -> float:
    ra = radiacao_extraterrestre_mj_m2_dia(LAT, dia)
    resultado = taxa_acumulo_safer(NDVI, RED, NIR, 20.0, 24.0, ra, ET0_ANUAL, 1.6)
    return resultado.taxa_acumulo_kg_ms_ha_dia


def _rodar(log: _Log, clima: list[ClimaDia] | None = None) -> EstadoProjetado:
    estado = projetar(log.eventos)
    centroides = {pid: (LAT, -50.0) for pid in estado.piquetes}
    if clima is None:
        clima = _clima(DATA_BASE - timedelta(days=10), DATA_BASE + timedelta(days=13))
    return projetar_estado(
        estado, log.eventos, CATALOGO, centroides, clima, ET0_ANUAL, LAT, DATA_BASE
    )


def test_projetar_estado_worked_example_medido_hoje() -> None:
    log = _Log()
    pid = log.piquete("P1", MARANDU)
    log.altura(pid, DATA_BASE, 30.0)
    log.leitura(pid, DATA_BASE - timedelta(days=2))
    (p,) = _rodar(log).piquetes
    assert p.massa_hoje_kg_ms_ha == pytest.approx(3300.0)
    assert p.altura_hoje_cm == pytest.approx(30.0)
    esperadas = [_taxa(DATA_BASE + timedelta(days=i)) for i in range(14)]
    assert p.taxa_acumulo_prevista_kg_ms_ha_dia == pytest.approx(esperadas)
    assert p.faltantes == ()
    assert p.dias_desde_imagem_limpa == 2
    assert p.confianca == Confianca.ALTA
    assert p.motivo_confianca == "última imagem de satélite sem nuvem há 2 dias"
    assert p.eficiencia_pastejo == pytest.approx(0.72)
    assert p.parametros is not None
    assert p.parametros.altura_entrada_cm == 25.0


def test_projetar_estado_simula_dias_com_lote() -> None:
    log = _Log()
    pid = log.piquete("P1", MARANDU)
    lote_id = log.lote()
    log.altura(pid, DATA_BASE - timedelta(days=3), 30.0)
    log.leitura(pid, DATA_BASE - timedelta(days=2))
    log.entrada(lote_id, pid, DATA_BASE - timedelta(days=1), OrigemEvento.SISTEMA)
    resultado = _rodar(log)
    (p,) = resultado.piquetes
    massa = 3300.0 + _taxa(DATA_BASE - timedelta(days=3)) + _taxa(DATA_BASE - timedelta(days=2))
    massa = avancar_massa_um_dia(massa, _taxa(DATA_BASE - timedelta(days=1)), 1113.75, 3.5, 0.72)
    assert p.massa_hoje_kg_ms_ha == pytest.approx(massa)
    assert p.altura_hoje_cm == pytest.approx(massa / 110.0)
    assert p.situacao == SituacaoPiquete.OCUPADO
    assert p.lote_atual_id == lote_id
    assert p.dias_descanso == 0
    assert p.confianca == Confianca.MEDIA
    assert p.motivo_confianca == "a última movimentação foi assumida sem confirmação sua"
    (lote,) = resultado.lotes
    assert lote.consumo_kg_ms_dia == pytest.approx(1113.75)
    assert lote.confianca_peso == Confianca.MEDIA
    assert lote.piquete_atual_id == pid


def test_projetar_estado_sem_regua() -> None:
    log = _Log()
    pid = log.piquete("P1", MARANDU)
    log.leitura(pid, DATA_BASE - timedelta(days=2))
    (p,) = _rodar(log).piquetes
    assert "altura_inicial" in p.faltantes
    assert p.massa_hoje_kg_ms_ha is None
    assert p.altura_hoje_cm is None
    assert p.taxa_acumulo_prevista_kg_ms_ha_dia == ()
    assert p.confianca == Confianca.BAIXA
    assert p.motivo_confianca == "nenhuma medição de altura com régua registrada para este piquete"
    assert p.dias_descanso == (DATA_BASE - date(2026, 1, 1)).days


def test_projetar_estado_mombaca_sem_densidade_e_ordem_por_nome() -> None:
    log = _Log()
    mid = log.piquete("B-Mombaça", MOMBACA)
    pid = log.piquete("A-Marandu", MARANDU)
    log.piquete("C-Inativo", MARANDU, ativo=False)
    for piquete_id in (mid, pid):
        log.altura(piquete_id, DATA_BASE, 30.0)
        log.leitura(piquete_id, DATA_BASE)
    a, b = _rodar(log).piquetes
    assert (a.nome, b.nome) == ("A-Marandu", "B-Mombaça")
    assert b.massa_hoje_kg_ms_ha is None
    assert b.faltantes == ("densidade_kg_ha_por_cm",)
    assert b.confianca == Confianca.BAIXA
    assert b.motivo_confianca == "a cultivar Mombaça ainda não tem calibração no SeuGado"


def test_projetar_estado_clima_faltando() -> None:
    log = _Log()
    pid = log.piquete("P1", MARANDU)
    log.altura(pid, DATA_BASE, 30.0)
    log.leitura(pid, DATA_BASE)
    clima = _clima(DATA_BASE, DATA_BASE + timedelta(days=13), pular=DATA_BASE + timedelta(days=5))
    (p,) = _rodar(log, clima).piquetes
    assert p.faltantes == ("clima",)
    assert p.massa_hoje_kg_ms_ha is None
    assert p.taxa_acumulo_prevista_kg_ms_ha_dia == ()
    assert p.motivo_confianca == "faltam dados de clima para o período"


def test_projetar_estado_imagem_antiga() -> None:
    log = _Log()
    pid = log.piquete("P1", MARANDU)
    log.altura(pid, DATA_BASE, 30.0)
    log.leitura(pid, DATA_BASE - timedelta(days=40))
    log.leitura(pid, DATA_BASE + timedelta(days=1))  # after data_base: ignored
    (p,) = _rodar(log).piquetes
    assert p.faltantes == ("imagem_satelite",)
    assert p.dias_desde_imagem_limpa == 40
    assert p.motivo_confianca == "nenhuma imagem de satélite sem nuvem nos últimos 30 dias"


def test_projetar_estado_continuo_ocupado_sem_eficiencia() -> None:
    log = _Log()
    pid = log.piquete("P1", MARANDU, metodo_pastejo="continuo")
    lote_id = log.lote()
    log.altura(pid, DATA_BASE - timedelta(days=2), 30.0)
    log.leitura(pid, DATA_BASE - timedelta(days=2))
    log.entrada(lote_id, pid, DATA_BASE - timedelta(days=1), OrigemEvento.PRODUTOR)
    (p,) = _rodar(log).piquetes
    assert p.faltantes == ("eficiencia_pastejo",)
    assert p.massa_hoje_kg_ms_ha is None
    assert p.motivo_confianca == "a cultivar Marandu ainda não tem calibração no SeuGado"


def test_estado_modules_are_pure() -> None:
    proibidos = {"psycopg", "httpx", "ee"}
    pasta = Path(__file__).parents[2] / "src" / "seugado" / "planner"
    for nome in ("estado.py", "estado_util.py"):
        arvore = ast.parse((pasta / nome).read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                raizes = {a.name.split(".")[0] for a in no.names}
            elif isinstance(no, ast.ImportFrom):
                raizes = {(no.module or "").split(".")[0]}
            else:
                continue
            assert not raizes & proibidos, nome


# --- montar_estado_projetado (R4) --------------------------------------------------------


class _Cursor:
    def __init__(self, respostas: dict[str, list[tuple[Any, ...]]]) -> None:
        self.respostas = respostas
        self.linhas: list[tuple[Any, ...]] = []

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, sql: str, _params: object = None) -> None:
        self.linhas = next(v for k, v in self.respostas.items() if k in sql)

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self.linhas

    def fetchone(self) -> tuple[Any, ...] | None:
        return self.linhas[0] if self.linhas else None


class _Conn:
    def __init__(self, respostas: dict[str, list[tuple[Any, ...]]]) -> None:
        self.respostas = respostas

    def cursor(self) -> _Cursor:
        return _Cursor(self.respostas)

    def commit(self) -> None:
        raise AssertionError("montar_estado_projetado must never commit")


def test_montar_estado_projetado(monkeypatch: pytest.MonkeyPatch) -> None:
    log = _Log()
    pid = log.piquete("P1", MARANDU)
    log.altura(pid, DATA_BASE - timedelta(days=3), 30.0)
    log.leitura(pid, DATA_BASE)
    chamadas: dict[str, Any] = {}

    def buscar_clima(*args: Any, **kwargs: Any) -> list[ClimaDia]:
        chamadas["clima"] = (args, kwargs)
        return _clima(args[2], args[3])

    monkeypatch.setattr(carga, "carregar_eventos", lambda _c, _f: log.eventos)
    monkeypatch.setattr(carga, "carregar_catalogo", lambda _c, _f: CATALOGO)
    monkeypatch.setattr(carga, "buscar_clima", buscar_clima)
    monkeypatch.setattr(carga, "et0_media_anual_mm_dia", lambda *_: ET0_ANUAL)
    conn = _Conn({"estado_piquete": [(pid, LAT, -50.0)], "fazenda": [("America/Sao_Paulo",)]})
    resultado = carga.montar_estado_projetado(conn, FAZENDA, DATA_BASE)  # type: ignore[arg-type]
    args, kwargs = chamadas["clima"]
    assert args == (LAT, -50.0, DATA_BASE - timedelta(days=3), DATA_BASE + timedelta(days=13))
    assert kwargs == {"hoje": DATA_BASE, "timezone": "America/Sao_Paulo"}
    (p,) = resultado.piquetes
    assert p.massa_hoje_kg_ms_ha is not None
    assert len(p.taxa_acumulo_prevista_kg_ms_ha_dia) == 14
    assert estado_para_dict(resultado)["piquetes"][0]["nome"] == "P1"


def test_montar_estado_projetado_sem_eventos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(carga, "carregar_eventos", lambda _c, _f: [])
    conn = _Conn({})
    resultado = carga.montar_estado_projetado(conn, FAZENDA, DATA_BASE)  # type: ignore[arg-type]
    assert resultado.piquetes == ()
    assert resultado.lotes == ()
