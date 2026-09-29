"""Autônomous routine for SeuGado."""
# ruff: noqa: PLC0415

import argparse
import logging
import os
import sys
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from seugado.cadastro.fazenda import carregar_fazenda
from seugado.contratos import PlanoManejo
from seugado.core.models import Fazenda

logger = logging.getLogger(__name__)

HORA_ROTINA_DIARIA = 6


def calcular_plano(
    conn: psycopg.Connection[Any], fazenda: Fazenda, hoje: date, ingerir_satelite: bool
) -> tuple[PlanoManejo, int]:
    """Calcula um novo plano para a fazenda."""
    from seugado.persistencia.projecao_db import reconstruir_projecao
    from seugado.planner.carga import montar_estado_projetado
    from seugado.planner.otimizador import gerar_plano
    from seugado.sensing.ingestao import ingerir_leituras

    if ingerir_satelite:
        novas = ingerir_leituras(conn, fazenda.id, hoje - timedelta(days=30), hoje)
    else:
        novas = 0

    reconstruir_projecao(conn, fazenda.id)
    conn.commit()  # leituras salvas mesmo se algo falhar depois
    estado = montar_estado_projetado(conn, fazenda.id, hoje)
    return gerar_plano(estado, fazenda, datetime.now(UTC), uuid4()), novas


def executar_ciclo(  # noqa: PLR0913, PLR0917
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    hoje: date | None = None,
    ingerir_satelite: bool = True,
    enviar: bool = True,
    atualizado: bool = False,
) -> PlanoManejo:
    """Calcula e JÁ coloca em vigor (botão da web e recálculo pedido pelo produtor no bot)."""
    from seugado.delivery.envio import enviar_plano
    from seugado.persistencia.planos import salvar_plano

    fazenda = carregar_fazenda(conn, fazenda_id)
    hoje = hoje or datetime.now(ZoneInfo(fazenda.timezone)).date()
    plano, _ = calcular_plano(conn, fazenda, hoje, ingerir_satelite)
    salvar_plano(conn, plano, "vigente")
    conn.commit()
    if enviar:
        enviar_plano(conn, plano, atualizado=atualizado)
    return plano


def entregar_plano_semanal(
    conn: psycopg.Connection[Any], fazenda_id: UUID, hoje: date, ingerir_satelite: bool = True
) -> PlanoManejo:
    """Calcula e envia o plano semanal."""
    plano = executar_ciclo(
        conn, fazenda_id, hoje, ingerir_satelite=ingerir_satelite, enviar=True
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE fazenda
            SET ultimo_envio_semanal = %s, ultima_rotina_diaria = %s
            WHERE id = %s
            """,
            (hoje, hoje, fazenda_id),
        )
    conn.commit()
    return plano


def rotina_diaria(
    conn: psycopg.Connection[Any], fazenda_id: UUID, hoje: date, ingerir_satelite: bool = True
) -> None:
    """Roda a rotina diária (satélite e mudanças)."""
    from seugado.delivery.confirmacao import lembrar_pendentes
    from seugado.delivery.envio import avisar_plano_candidato
    from seugado.persistencia.planos import carregar_plano_atual, ids_respondidos, salvar_plano
    from seugado.planner.comparacao import comparar_planos

    lembrar_pendentes(conn, fazenda_id, hoje)
    fazenda = carregar_fazenda(conn, fazenda_id)
    vigente = carregar_plano_atual(conn, fazenda_id)
    novo, novas = calcular_plano(conn, fazenda, hoje, ingerir_satelite=ingerir_satelite)

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE fazenda SET ultima_rotina_diaria = %s WHERE id = %s",
            (hoje, fazenda_id),
        )
    conn.commit()

    if vigente is None or novas == 0:
        return

    difs = comparar_planos(vigente, novo, ids_respondidos(conn, fazenda_id), hoje)
    if difs:
        salvar_plano(conn, novo, "candidato")
        conn.commit()
        avisar_plano_candidato(conn, novo, difs)


def executar_agenda(agora_utc: datetime | None = None) -> int:
    """Roda de hora em hora para todas as fazendas. Devolve 0 se sucesso, 1 se falha."""
    agora = agora_utc or datetime.now(UTC)
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set")
        return 1

    falhou = False
    conn = psycopg.connect(db_url, autocommit=False)
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT f.id, f.timezone, f.envio_plano_dia, f.envio_plano_hora,
                       f.ultimo_envio_semanal, f.ultima_rotina_diaria
                FROM fazenda f
                WHERE f.ativo = TRUE
                  AND EXISTS (
                      SELECT 1 FROM estado_piquete ep
                      WHERE ep.fazenda_id = f.id AND ep.ativo = TRUE
                  )
                """
            )
            fazendas = cur.fetchall()

        for f_row in fazendas:
            fazenda_id = f_row["id"]
            tz = ZoneInfo(f_row["timezone"])
            local = agora.astimezone(tz)
            hoje = local.date()

            try:
                if (
                    local.weekday() == f_row["envio_plano_dia"]
                    and local.hour >= f_row["envio_plano_hora"]
                    and f_row["ultimo_envio_semanal"] != hoje
                ):
                    entregar_plano_semanal(conn, fazenda_id, hoje)
                elif (
                    local.hour >= HORA_ROTINA_DIARIA
                    and f_row["ultima_rotina_diaria"] != hoje
                ):
                    rotina_diaria(conn, fazenda_id, hoje)
            except Exception as e:
                conn.rollback()
                logger.exception("Falha na fazenda %s: %s", fazenda_id, e)
                falhou = True

    finally:
        conn.close()

    return 1 if falhou else 0


def main() -> None:
    """Entrypoint CLI."""
    parser = argparse.ArgumentParser(description="Rotina SeuGado")
    parser.add_argument("--agenda", action="store_true", help="Executar agenda")
    parser.add_argument("--fazenda", type=UUID, help="ID da fazenda")
    parser.add_argument("--entregar", action="store_true", help="Força entrega semanal")
    parser.add_argument("--diaria", action="store_true", help="Força rotina diária")
    parser.add_argument("--recalcular", action="store_true", help="Recalcula e ativa")
    parser.add_argument("--sem-satelite", action="store_true", help="Não baixar")
    parser.add_argument("--sem-envio", action="store_true", help="Não enviar mensagens")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    ingerir_satelite = not args.sem_satelite
    enviar = not args.sem_envio

    if args.agenda:
        sys.exit(executar_agenda())

    if args.fazenda:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            sys.exit("DATABASE_URL not set")

        conn = psycopg.connect(db_url, autocommit=False)
        try:
            fazenda = carregar_fazenda(conn, args.fazenda)
            hoje = datetime.now(ZoneInfo(fazenda.timezone)).date()

            if args.entregar:
                entregar_plano_semanal(conn, args.fazenda, hoje, ingerir_satelite=ingerir_satelite)
                if not enviar:
                    logger.warning("Plano foi enviado pois --entregar forca o envio.")
            elif args.diaria:
                rotina_diaria(conn, args.fazenda, hoje, ingerir_satelite=ingerir_satelite)
            elif args.recalcular:
                executar_ciclo(
                    conn, args.fazenda, hoje,
                    ingerir_satelite=ingerir_satelite,
                    enviar=enviar
                )
        finally:
            conn.close()
        sys.exit(0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
