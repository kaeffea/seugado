"""Testes para o ciclo."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from seugado.jobs.ciclo import executar_agenda, executar_ciclo, main, rotina_diaria


@pytest.fixture
def conn():
    return MagicMock()


@pytest.fixture
def mock_deps():
    with patch("seugado.jobs.ciclo.carregar_fazenda") as mock_carregar, \
         patch("seugado.jobs.ciclo.os.environ.get") as mock_env, \
         patch("seugado.jobs.ciclo.psycopg.connect") as mock_connect, \
         patch("seugado.jobs.ciclo.calcular_plano") as mock_calcular, \
         patch("seugado.jobs.ciclo.sys.exit") as mock_exit:
         
        mock_env.return_value = "fake_url"
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_exit.side_effect = SystemExit
        
        fazenda = MagicMock()
        fazenda.id = uuid4()
        fazenda.timezone = "America/Fortaleza"
        mock_carregar.return_value = fazenda
        
        yield {
            "carregar_fazenda": mock_carregar,
            "os_env": mock_env,
            "psycopg_connect": mock_connect,
            "mock_conn": mock_conn,
            "calcular_plano": mock_calcular,
            "sys_exit": mock_exit,
            "fazenda": fazenda,
        }


def test_ordem_chamadas_executar_ciclo(mock_deps, conn):
    """Verifica a ordem em executar_ciclo."""
    mock_envio = MagicMock()
    mock_planos = MagicMock()
    
    with patch.dict("sys.modules", {
        "seugado.delivery.envio": mock_envio,
        "seugado.persistencia.planos": mock_planos,
    }):
        plano_falso = MagicMock()
        mock_deps["calcular_plano"].return_value = (plano_falso, 0)
        
        executar_ciclo(conn, uuid4())
        
        mock_deps["calcular_plano"].assert_called_once()
        mock_planos.salvar_plano.assert_called_once_with(conn, plano_falso, "vigente")
        conn.commit.assert_called()
        mock_envio.enviar_plano.assert_called_once_with(conn, plano_falso, atualizado=False)


def test_rotina_diaria_candidato_apenas_com_diferenca(mock_deps, conn):
    """Candidato só é salvo e avisado quando há leitura nova e diferença."""
    mock_confirmacao = MagicMock()
    mock_envio = MagicMock()
    mock_planos = MagicMock()
    mock_comparacao = MagicMock()
    
    with patch.dict("sys.modules", {
        "seugado.delivery.confirmacao": mock_confirmacao,
        "seugado.delivery.envio": mock_envio,
        "seugado.persistencia.planos": mock_planos,
        "seugado.planner.comparacao": mock_comparacao,
    }):
        hoje = date(2026, 9, 20)
        plano_novo = MagicMock()
        mock_planos.carregar_plano_atual.return_value = MagicMock()
        
        # Caso 1: sem leitura nova (novas=0)
        mock_deps["calcular_plano"].return_value = (plano_novo, 0)
        rotina_diaria(conn, uuid4(), hoje)
        mock_comparacao.comparar_planos.assert_not_called()
        mock_planos.salvar_plano.assert_not_called()
        
        # Caso 2: leitura nova (novas=5), mas sem diferença
        mock_deps["calcular_plano"].return_value = (plano_novo, 5)
        mock_comparacao.comparar_planos.return_value = []
        rotina_diaria(conn, uuid4(), hoje)
        mock_planos.salvar_plano.assert_not_called()
        mock_envio.avisar_plano_candidato.assert_not_called()
        
        # Caso 3: leitura nova e com diferença
        mock_comparacao.comparar_planos.return_value = ["diff"]
        rotina_diaria(conn, uuid4(), hoje)
        mock_planos.salvar_plano.assert_called_once_with(conn, plano_novo, "candidato")
        mock_envio.avisar_plano_candidato.assert_called_once_with(conn, plano_novo, ["diff"])


def test_executar_agenda_comportamento(mock_deps):
    """Verifica comportamento da agenda: erro de uma não afeta outra, e horários."""
    # 21 = Segunda (weekday=0)
    hoje_local = datetime(2026, 9, 21, 6, 0, tzinfo=ZoneInfo("America/Fortaleza"))
    
    # 2 fazendas ativas
    f1_id, f2_id = uuid4(), uuid4()
    mock_deps["mock_conn"].cursor.return_value.__enter__.return_value.fetchall.return_value = [
        {
            "id": f1_id, "timezone": "America/Fortaleza", "envio_plano_dia": 0,
            "envio_plano_hora": 6, "ultimo_envio_semanal": date(2026, 9, 14),
            "ultima_rotina_diaria": date(2026, 9, 20)
        },
        {
            "id": f2_id, "timezone": "America/Fortaleza",
            "envio_plano_dia": 1, # Terça, logo cai na diária
            "envio_plano_hora": 6, "ultimo_envio_semanal": date(2026, 9, 14),
            "ultima_rotina_diaria": date(2026, 9, 20)
        }
    ]
    
    with patch("seugado.jobs.ciclo.entregar_plano_semanal") as mock_entregar, \
         patch("seugado.jobs.ciclo.rotina_diaria") as mock_diaria:
         
        # Fazenda 1 falha na entrega
        mock_entregar.side_effect = Exception("Erro F1")
        
        ret = executar_agenda(agora_utc=hoje_local.astimezone(UTC))
        
        assert ret == 1
        mock_entregar.assert_called_once_with(mock_deps["mock_conn"], f1_id, hoje_local.date())
        # F2 tenta rodar diária apesar de F1 falhar
        mock_diaria.assert_called_once_with(mock_deps["mock_conn"], f2_id, hoje_local.date())
        mock_deps["mock_conn"].rollback.assert_called_once()
        
        # Fazenda 1 não roda entrega se for mesmo dia
        mock_entregar.reset_mock()
        mock_diaria.reset_mock()
        mock_deps["mock_conn"].cursor.return_value.__enter__.return_value.fetchall.return_value = [
            {
                "id": f1_id, "timezone": "America/Fortaleza", "envio_plano_dia": 0,
                "envio_plano_hora": 6, "ultimo_envio_semanal": hoje_local.date(),
                "ultima_rotina_diaria": hoje_local.date()
            }
        ]
        ret = executar_agenda(agora_utc=hoje_local.astimezone(UTC))
        assert ret == 0
        mock_entregar.assert_not_called()
        mock_diaria.assert_not_called()


@patch(
    "seugado.jobs.ciclo.sys.argv",
    ["ciclo", "--fazenda", str(uuid4()), "--recalcular", "--sem-satelite"]
)
def test_main_cli_sem_satelite(mock_deps):
    """Testa --fazenda <id> --recalcular --sem-satelite não chama Earth Engine."""
    with patch("seugado.jobs.ciclo.executar_ciclo") as mock_ciclo:
        with pytest.raises(SystemExit):
            main()
        mock_deps["sys_exit"].assert_called_with(0)
        mock_ciclo.assert_called_once()
        assert mock_ciclo.call_args.kwargs["ingerir_satelite"] is False
