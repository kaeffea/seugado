"""T4: producer answers as events, destination rules and the daily reminder."""

import math
import sys
import uuid
from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

import psycopg
import pytest

from seugado.contratos import Movimentacao, PlanoManejo
from seugado.delivery import confirmacao
from seugado.delivery.confirmacao import (
    RespostaInvalida,
    lembrar_pendentes,
    piquetes_livres,
    registrar_altura,
    registrar_avulsa,
    registrar_diferente,
    registrar_fiz,
    registrar_nao_fiz,
    resposta_existente,
)
from seugado.delivery.mensagem import botoes_lembrete, texto_lembrete
from tests.delivery.banco import (
    PIQUETE_INATIVO,
    RECRIA,
    VACAS,
    FazendaTeste,
    criar_fazenda,
    piquete,
    requer_banco,
)
from tests.delivery.falsos import CanalFalso, Enviado, conexao_falsa, modulo_falso

CHAT_ID = 123456789
ATOR = "telegram:123456789"
SEG, QUA, QUI = date(2026, 9, 28), date(2026, 9, 30), date(2026, 10, 1)


def _instalar_planos(
    monkeypatch: pytest.MonkeyPatch, plano: PlanoManejo | None, respondidas: frozenset[uuid.UUID]
) -> None:
    modulo = modulo_falso(
        "seugado.persistencia.planos",
        carregar_plano_atual=lambda conn, fazenda_id: plano,
        ids_respondidos=lambda conn, fazenda_id: respondidas,
    )
    monkeypatch.setitem(sys.modules, "seugado.persistencia.planos", modulo)


# --- without a database -------------------------------------------------------------------


def test_lembrete_so_de_movimentacoes_passadas_sem_resposta(
    plano: PlanoManejo, monkeypatch: pytest.MonkeyPatch
) -> None:
    recria_seg, vacas_seg, _vacas_qui = plano.movimentacoes
    _instalar_planos(monkeypatch, plano, frozenset({recria_seg.id}))
    conn, falsa = conexao_falsa(("Fazenda Exemplo", CHAT_ID))
    canal = CanalFalso()
    assert lembrar_pendentes(conn, plano.fazenda_id, QUI, canal=canal) == 1
    assert canal.enviados == [
        Enviado(CHAT_ID, texto_lembrete([vacas_seg]), botoes_lembrete([vacas_seg]))
    ]
    assert all(sql.lstrip().upper().startswith("SELECT") for sql, _ in falsa.consultas)
    assert falsa.commits == 0


def test_lembrete_nao_manda_nada_sem_pendencia(
    plano: PlanoManejo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Movements of today are not overdue yet: only mov.data < hoje counts."""
    _instalar_planos(monkeypatch, plano, frozenset())
    conn, _ = conexao_falsa(("Fazenda Exemplo", CHAT_ID))
    canal = CanalFalso()
    assert lembrar_pendentes(conn, plano.fazenda_id, SEG, canal=canal) == 0
    _instalar_planos(monkeypatch, None, frozenset())
    assert lembrar_pendentes(conn, plano.fazenda_id, QUI, canal=canal) == 0
    assert canal.enviados == []


def test_lembrete_sem_chat_nao_lembra_ninguem(
    plano: PlanoManejo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _instalar_planos(monkeypatch, plano, frozenset())
    conn, _ = conexao_falsa(("Fazenda Exemplo", None))
    canal = CanalFalso()
    assert lembrar_pendentes(conn, plano.fazenda_id, QUI, canal=canal) == 0
    assert canal.enviados == []


@pytest.mark.parametrize("altura", [0.0, -1.0, 400.1, math.nan, math.inf])
def test_altura_fora_da_faixa_nao_toca_no_banco(altura: float) -> None:
    conn, falsa = conexao_falsa(("qualquer",))
    with pytest.raises(RespostaInvalida, match="maior que 0 e no máximo 400 cm"):
        registrar_altura(conn, uuid.uuid4(), piquete(4), altura, QUA, ATOR)
    assert falsa.consultas == []


# --- with the test database (rolled back; commit() fails) ---------------------------------


@pytest.fixture
def fazenda(conn_banco: psycopg.Connection[Any]) -> FazendaTeste:
    return criar_fazenda(conn_banco)


@pytest.fixture
def movs(plano: PlanoManejo, fazenda: FazendaTeste) -> tuple[Movimentacao, ...]:
    """(Recria P2→P6 seg, Vacas P5→P1 seg, Vacas P1→P3 qui), same ids as the fixture."""
    return plano.movimentacoes


def _hoje_local() -> date:
    return datetime.now(ZoneInfo("America/Fortaleza")).date()


def _eventos(conn: psycopg.Connection[Any], fazenda_id: uuid.UUID, tipo: str) -> list[Any]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT payload, origem, ator, chave_idempotencia FROM evento"
            " WHERE fazenda_id = %s AND tipo = %s ORDER BY sequencia",
            (fazenda_id, tipo),
        )
        return cur.fetchall()


def _total_eventos(conn: psycopg.Connection[Any], fazenda_id: uuid.UUID) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM evento WHERE fazenda_id = %s", (fazenda_id,))
        linha = cur.fetchone()
    assert linha is not None
    return int(linha[0])


def _piquete_do_lote(
    conn: psycopg.Connection[Any], fazenda_id: uuid.UUID, lote_id: uuid.UUID
) -> uuid.UUID | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT piquete_atual_id FROM estado_lote WHERE fazenda_id = %s AND lote_id = %s",
            (fazenda_id, lote_id),
        )
        linha = cur.fetchone()
    assert linha is not None
    return cast("uuid.UUID | None", linha[0])


@requer_banco
def test_fiz_grava_confirmado_e_move_o_lote(
    conn_banco: psycopg.Connection[Any], fazenda: FazendaTeste, movs: tuple[Movimentacao, ...]
) -> None:
    mov = movs[0]
    assert resposta_existente(conn_banco, fazenda.id, mov.id) is None
    registrar_fiz(conn_banco, fazenda.id, mov, QUI, ATOR)
    assert _eventos(conn_banco, fazenda.id, "manejo_confirmado")[-1] == (
        {
            "entidade_id": str(mov.id),
            "lote_id": str(RECRIA),
            "piquete_destino_id": str(piquete(6)),
            "data_execucao": "2026-09-28",
        },
        "produtor",
        ATOR,
        f"resposta:{mov.id}",
    )
    assert _piquete_do_lote(conn_banco, fazenda.id, RECRIA) == piquete(6)
    assert resposta_existente(conn_banco, fazenda.id, mov.id) == "manejo_confirmado"


@requer_banco
def test_fiz_antes_do_dia_vale_hoje(
    conn_banco: psycopg.Connection[Any], fazenda: FazendaTeste, movs: tuple[Movimentacao, ...]
) -> None:
    registrar_fiz(conn_banco, fazenda.id, movs[2], QUA, ATOR)
    payload = _eventos(conn_banco, fazenda.id, "manejo_confirmado")[-1][0]
    assert payload["data_execucao"] == "2026-09-30"


@requer_banco
def test_fiz_duas_vezes_gera_um_unico_evento(
    conn_banco: psycopg.Connection[Any],
    fazenda: FazendaTeste,
    movs: tuple[Movimentacao, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mov = movs[0]
    registrar_fiz(conn_banco, fazenda.id, mov, QUI, ATOR)
    with pytest.raises(RespostaInvalida, match="já respondeu"):
        registrar_fiz(conn_banco, fazenda.id, mov, QUI, ATOR)
    # Two simultaneous taps can both pass the check; the idempotency key still holds.
    monkeypatch.setattr(confirmacao, "resposta_existente", lambda *args: None)
    registrar_fiz(conn_banco, fazenda.id, mov, QUI, ATOR)
    chaves = [linha[3] for linha in _eventos(conn_banco, fazenda.id, "manejo_confirmado")]
    assert chaves.count(f"resposta:{mov.id}") == 1


@requer_banco
def test_nao_fiz_grava_recusado_e_lote_fica(
    conn_banco: psycopg.Connection[Any], fazenda: FazendaTeste, movs: tuple[Movimentacao, ...]
) -> None:
    mov = movs[0]
    registrar_nao_fiz(conn_banco, fazenda.id, mov, ATOR)
    assert _eventos(conn_banco, fazenda.id, "manejo_recusado") == [
        ({"entidade_id": str(mov.id), "motivo": None}, "produtor", ATOR, f"resposta:{mov.id}")
    ]
    assert _piquete_do_lote(conn_banco, fazenda.id, RECRIA) == piquete(2)
    assert resposta_existente(conn_banco, fazenda.id, mov.id) == "manejo_recusado"


@requer_banco
def test_segunda_resposta_diferente_e_recusada(
    conn_banco: psycopg.Connection[Any], fazenda: FazendaTeste, movs: tuple[Movimentacao, ...]
) -> None:
    mov = movs[0]
    registrar_fiz(conn_banco, fazenda.id, mov, QUI, ATOR)
    with pytest.raises(RespostaInvalida, match="já respondeu"):
        registrar_nao_fiz(conn_banco, fazenda.id, mov, ATOR)
    with pytest.raises(RespostaInvalida, match="já respondeu"):
        registrar_diferente(
            conn_banco, fazenda.id, mov, piquete(4), _hoje_local() - timedelta(days=1), ATOR
        )
    assert _eventos(conn_banco, fazenda.id, "manejo_recusado") == []
    assert _eventos(conn_banco, fazenda.id, "manejo_divergente") == []


@requer_banco
def test_diferente_grava_divergente_e_move_o_lote(
    conn_banco: psycopg.Connection[Any], fazenda: FazendaTeste, movs: tuple[Movimentacao, ...]
) -> None:
    mov = movs[0]
    ontem = _hoje_local() - timedelta(days=1)
    registrar_diferente(conn_banco, fazenda.id, mov, piquete(4), ontem, ATOR)
    assert _eventos(conn_banco, fazenda.id, "manejo_divergente") == [
        (
            {
                "entidade_id": str(mov.id),
                "lote_id": str(RECRIA),
                "piquete_real_id": str(piquete(4)),
                "data_execucao": ontem.isoformat(),
                "observacao": None,
            },
            "produtor",
            ATOR,
            f"resposta:{mov.id}",
        )
    ]
    assert _piquete_do_lote(conn_banco, fazenda.id, RECRIA) == piquete(4)


@requer_banco
@pytest.mark.parametrize(
    ("n_piquete", "dias", "erro"),
    [
        (5, -1, "Piquete 5 está com o lote Vacas com bezerro"),
        (2, -1, "O lote Recria já está nesse piquete"),
        (PIQUETE_INATIVO, -1, "Piquete 9 não está ativo"),
        (99, -1, "Não encontrei esse piquete"),
        (4, 1, "não pode ser depois de hoje"),
    ],
)
def test_diferente_recusa_destino_invalido(
    conn_banco: psycopg.Connection[Any],
    fazenda: FazendaTeste,
    movs: tuple[Movimentacao, ...],
    n_piquete: int,
    dias: int,
    erro: str,
) -> None:
    data = _hoje_local() + timedelta(days=dias)
    with pytest.raises(RespostaInvalida, match=erro):
        registrar_diferente(conn_banco, fazenda.id, movs[0], piquete(n_piquete), data, ATOR)
    assert _eventos(conn_banco, fazenda.id, "manejo_divergente") == []
    assert resposta_existente(conn_banco, fazenda.id, movs[0].id) is None


@requer_banco
def test_piquetes_livres_sao_os_ativos_e_vazios(
    conn_banco: psycopg.Connection[Any], fazenda: FazendaTeste, movs: tuple[Movimentacao, ...]
) -> None:
    livres = piquetes_livres(conn_banco, fazenda.id)
    assert livres == [(piquete(n), f"Piquete {n}") for n in (1, 3, 4, 6, 7, 8)]
    registrar_fiz(conn_banco, fazenda.id, movs[0], QUI, ATOR)  # Recria: P2 -> P6
    assert [n for n, _ in piquetes_livres(conn_banco, fazenda.id)] == [
        piquete(n) for n in (1, 2, 3, 4, 7, 8)
    ]


@requer_banco
def test_avulsa_grava_confirmado_com_id_novo(
    conn_banco: psycopg.Connection[Any], fazenda: FazendaTeste, movs: tuple[Movimentacao, ...]
) -> None:
    hoje = _hoje_local()
    registrar_avulsa(conn_banco, fazenda.id, VACAS, piquete(4), hoje, ATOR)
    payload, origem, ator, chave = _eventos(conn_banco, fazenda.id, "manejo_confirmado")[-1]
    assert payload["lote_id"] == str(VACAS)
    assert payload["piquete_destino_id"] == str(piquete(4))
    assert payload["data_execucao"] == hoje.isoformat()
    assert payload["entidade_id"] not in {str(mov.id) for mov in movs}
    assert (origem, ator, chave) == ("produtor", ATOR, None)
    assert _piquete_do_lote(conn_banco, fazenda.id, VACAS) == piquete(4)


@requer_banco
def test_avulsa_recusa_lote_desconhecido_e_piquete_ocupado(
    conn_banco: psycopg.Connection[Any], fazenda: FazendaTeste
) -> None:
    hoje = _hoje_local()
    with pytest.raises(RespostaInvalida, match="Não encontrei esse lote"):
        registrar_avulsa(conn_banco, fazenda.id, uuid.uuid4(), piquete(4), hoje, ATOR)
    with pytest.raises(RespostaInvalida, match="está com o lote Recria"):
        registrar_avulsa(conn_banco, fazenda.id, VACAS, piquete(2), hoje, ATOR)


@requer_banco
def test_altura_grava_medida_do_bot(
    conn_banco: psycopg.Connection[Any], fazenda: FazendaTeste
) -> None:
    registrar_altura(conn_banco, fazenda.id, piquete(4), 28.0, QUA, ATOR)
    registrar_altura(conn_banco, fazenda.id, piquete(1), 400.0, QUA, ATOR)
    ((payload, origem, ator, chave), _) = _eventos(conn_banco, fazenda.id, "altura_medida")
    assert payload["piquete_id"] == str(piquete(4))
    assert (payload["data"], payload["altura_cm"], payload["meio"]) == ("2026-09-30", 28.0, "bot")
    assert (origem, ator, chave) == ("produtor", ATOR, None)
    with conn_banco.cursor() as cur:
        cur.execute(
            "SELECT altura_cm, meio FROM altura_atual WHERE fazenda_id = %s AND piquete_id = %s",
            (fazenda.id, piquete(4)),
        )
        assert cur.fetchone() == (28.0, "bot")
    with pytest.raises(RespostaInvalida, match="Não encontrei esse piquete"):
        registrar_altura(conn_banco, fazenda.id, uuid.uuid4(), 28.0, QUA, ATOR)


@requer_banco
def test_lembrete_nao_grava_evento(
    conn_banco: psycopg.Connection[Any],
    fazenda: FazendaTeste,
    plano: PlanoManejo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_planos(monkeypatch, replace(plano, fazenda_id=fazenda.id), frozenset())
    antes = _total_eventos(conn_banco, fazenda.id)
    canal = CanalFalso()
    assert lembrar_pendentes(conn_banco, fazenda.id, QUI, canal=canal) == 2
    assert _total_eventos(conn_banco, fazenda.id) == antes
    assert canal.enviados[0].chat_id == fazenda.chat_id
