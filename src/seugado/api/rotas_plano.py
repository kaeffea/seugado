"""Plano routes (owner: Leandro): current plan, run the cycle now, Telegram link."""

import os
from typing import Any

import ee
import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from seugado.api.auth import FazendaAutorizada, Usuario
from seugado.api.deps import Conexao
from seugado.contratos import plano_para_dict
from seugado.delivery.canais.telegram import ErroTelegram
from seugado.jobs.ciclo import executar_ciclo
from seugado.persistencia.planos import carregar_plano_atual

router = APIRouter(tags=["plano"])

# Weather (Open-Meteo), satellite (Earth Engine) and Telegram failures are not our bug: 502.
_ERROS_EXTERNOS = (httpx.HTTPError, ee.EEException, ErroTelegram)


class CicloIn(BaseModel):
    """Body of POST /ciclo."""

    ingerir_satelite: bool = True
    enviar: bool = True


@router.get("/fazendas/{fazenda_id}/plano/atual")
def obter_plano_atual(
    fazenda_id: FazendaAutorizada, usuario: Usuario, conn: Conexao
) -> dict[str, Any]:
    """The plan in force (vigente), or 404."""
    plano = carregar_plano_atual(conn, fazenda_id)
    if plano is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ainda não há plano")
    return plano_para_dict(plano)


@router.post("/fazendas/{fazenda_id}/ciclo")
def rodar_ciclo(
    fazenda_id: FazendaAutorizada, usuario: Usuario, conn: Conexao, corpo: CicloIn | None = None
) -> dict[str, Any]:
    """Compute the plan now and put it in force; may take 1–2 minutes with the satellite."""
    dados = corpo or CicloIn()
    try:
        plano = executar_ciclo(
            conn, fazenda_id, ingerir_satelite=dados.ingerir_satelite, enviar=dados.enviar
        )
        conn.commit()
    except _ERROS_EXTERNOS as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
    return plano_para_dict(plano)


@router.get("/fazendas/{fazenda_id}/telegram")
def obter_telegram(
    fazenda_id: FazendaAutorizada, usuario: Usuario, conn: Conexao
) -> dict[str, Any]:
    """Whether the farm's Telegram is linked, and the link the producer opens to link it."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT telegram_chat_id IS NOT NULL, codigo_vinculo_telegram FROM fazenda"
            " WHERE id = %s",
            (fazenda_id,),
        )
        row = cur.fetchone()
    if row is None:  # FazendaAutorizada already checked; kept for the type checker
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fazenda não encontrada")
    vinculado, codigo = row
    bot = os.environ.get("TELEGRAM_BOT_USERNAME", "")
    return {"vinculado": bool(vinculado), "link": f"https://t.me/{bot}?start={codigo}"}
