"""Smoke checks for the walking distance through feeding squares and candidate paddocks."""

import ast
import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from seugado.contratos import EstadoProjetado, LoteProjetado, PiqueteProjetado, estado_de_dict
from seugado.planner import estrutura
from seugado.planner.estrutura import (
    RAIO_TERRA_M,
    distancia_manejo_m,
    haversine_m,
    piquetes_candidatos,
    ponto_acesso,
)

PRACA = (-9.6000, -36.0000)
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "estado_projetado_exemplo.json"


def _estado_base() -> EstadoProjetado:
    with FIXTURE.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return estado_de_dict(data)


def _piquete(lat: float, lon: float, **extra: Any) -> PiqueteProjetado:
    base = _estado_base().piquetes[0]
    return replace(base, piquete_id=uuid4(), centroide_lat=lat, centroide_lon=lon, **extra)


def _na_praca(piquete: PiqueteProjetado, lat: float, lon: float) -> PiqueteProjetado:
    return replace(piquete, praca_id=uuid4(), praca_lat=lat, praca_lon=lon)


def test_haversine_um_grau_de_latitude() -> None:
    assert haversine_m(0.0, 0.0, 1.0, 0.0) == pytest.approx(RAIO_TERRA_M * 3.141592653589793 / 180)
    assert haversine_m(-9.6, -36.0, -9.6, -36.0) == 0.0


def test_haversine_rejeita_coordenada_fora_da_faixa() -> None:
    with pytest.raises(ValueError):
        haversine_m(91.0, 0.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        haversine_m(0.0, 0.0, 0.0, -181.0)


def test_exemplo_trabalhado_mesma_praca_e_sem_praca() -> None:
    a = _piquete(-9.6010, -36.0000)
    b = _piquete(-9.6000, -36.0010)
    assert distancia_manejo_m(a, b) == pytest.approx(156.16, abs=0.5)  # centroids, no square
    a_p, b_p = _na_praca(a, *PRACA), _na_praca(b, *PRACA)
    assert distancia_manejo_m(a_p, b_p) == pytest.approx(220.83, abs=0.5)
    assert distancia_manejo_m(a_p, b_p) == pytest.approx(
        haversine_m(-9.6010, -36.0, *PRACA) + haversine_m(*PRACA, -9.6, -36.0010)
    )


def test_duas_pracas_somam_o_trecho_reto_entre_elas() -> None:
    a = _na_praca(_piquete(-9.6010, -36.0000), *PRACA)
    c = _na_praca(_piquete(-9.6060, -36.0040), -9.6050, -36.0040)
    assert distancia_manejo_m(a, c) == pytest.approx(930.51, abs=0.5)
    assert distancia_manejo_m(a, c) == pytest.approx(distancia_manejo_m(c, a), abs=1e-6)


def test_so_o_destino_com_praca_usa_o_centroide_da_origem() -> None:
    a = _piquete(-9.6010, -36.0000)
    b = _na_praca(_piquete(-9.6000, -36.0010), *PRACA)
    assert distancia_manejo_m(a, b) == pytest.approx(220.83, abs=0.5)


def test_mesmo_piquete_e_zero_mesmo_com_praca() -> None:
    a = _na_praca(_piquete(-9.6010, -36.0000), *PRACA)
    assert distancia_manejo_m(a, a) == 0.0


def test_ponto_acesso_prefere_a_praca_e_exige_o_par() -> None:
    p = _piquete(-9.6010, -36.0000)
    assert ponto_acesso(p) == (-9.6010, -36.0000)
    assert ponto_acesso(_na_praca(p, *PRACA)) == PRACA
    for incompleto in (replace(p, praca_lat=-9.6), replace(p, praca_lon=-36.0)):
        with pytest.raises(ValueError):
            ponto_acesso(incompleto)


def test_candidatos_filtram_pelo_modulo_do_lote() -> None:
    estado = _estado_base()
    m1, m2 = UUID(int=1), UUID(int=2)
    modulos = [m1, m2, None, m1] + [m2] * (len(estado.piquetes) - 4)
    piquetes = tuple(replace(p, modulo_id=m) for p, m in zip(estado.piquetes, modulos, strict=True))
    estado = replace(estado, piquetes=piquetes)
    lote: LoteProjetado = estado.lotes[0]

    com_modulo = piquetes_candidatos(estado, replace(lote, modulo_id=m1))
    assert [p.piquete_id for p in com_modulo] == [piquetes[0].piquete_id, piquetes[3].piquete_id]

    sem_modulo = piquetes_candidatos(estado, replace(lote, modulo_id=None))
    assert sem_modulo == piquetes

    outro = piquetes_candidatos(estado, replace(lote, modulo_id=UUID(int=99)))
    assert outro == ()


def test_modulo_e_so_funcoes_puras_com_imports_permitidos() -> None:
    arvore = ast.parse(Path(estrutura.__file__).read_text(encoding="utf-8"))
    raizes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            raizes |= {a.name.split(".")[0] for a in no.names}
        elif isinstance(no, ast.ImportFrom):
            raizes.add((no.module or "").split(".")[0])
    assert raizes <= {"math", "uuid", "seugado"}
    publicos = {
        n
        for n, v in vars(estrutura).items()
        if not n.startswith("_") and getattr(v, "__module__", None) == estrutura.__name__
    }
    assert publicos == {"haversine_m", "ponto_acesso", "distancia_manejo_m", "piquetes_candidatos"}
