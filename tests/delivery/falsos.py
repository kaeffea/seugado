"""Test doubles shared by the delivery tests."""

from collections.abc import Sequence
from dataclasses import dataclass

from seugado.delivery.canais.base import Botao


@dataclass(frozen=True)
class Enviado:
    chat_id: int
    texto: str
    botoes: list[list[Botao]]


class CanalFalso:
    """Canal that records what would have reached the producer."""

    def __init__(self) -> None:
        self.enviados: list[Enviado] = []
        self.cliques: list[tuple[str, str | None]] = []

    def enviar_texto(
        self, chat_id: int, texto: str, botoes: Sequence[Sequence[Botao]] = ()
    ) -> None:
        self.enviados.append(Enviado(chat_id, texto, [list(linha) for linha in botoes]))

    def responder_clique(self, id_clique: str, texto: str | None = None) -> None:
        self.cliques.append((id_clique, texto))
