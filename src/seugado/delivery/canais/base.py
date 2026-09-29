"""Messaging channel interface: delivery code talks to this, never to Telegram directly."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

MAX_BYTES_DADOS_BOTAO = 64


@dataclass(frozen=True, slots=True)
class Botao:
    """One inline button: the label the producer sees and the data sent back on tap."""

    texto: str
    dados: str  # callback_data: 1 to 64 bytes

    def __post_init__(self) -> None:
        tamanho = len(self.dados.encode("utf-8"))
        if not 0 < tamanho <= MAX_BYTES_DADOS_BOTAO:
            raise ValueError(f"button data must have 1 to 64 bytes, got {tamanho}: {self.dados!r}")


class Canal(Protocol):
    """What delivery needs from a messenger (Telegram now, WhatsApp later: ADR-006)."""

    def enviar_texto(
        self, chat_id: int, texto: str, botoes: Sequence[Sequence[Botao]] = ()
    ) -> None:
        """Send an HTML text, with one inline keyboard row per inner sequence."""

    def responder_clique(self, id_clique: str, texto: str | None = None) -> None:
        """Acknowledge a button tap, optionally with a short toast."""
