"""Price guard: every amount in a reply must have come from a tool output or from the customer.

Manual §7.1: never give prices, stock or deadlines without checking the system; a wrong price can
count as misleading advertising. A prompt asks for that; this check enforces it.
"""

from __future__ import annotations

from decimal import Decimal

from emporio.money import brl, money_mentions

FALLBACK = (
    "Quero te passar os valores certinhos, então deixa eu conferir no sistema antes. "
    "Me confirma qual produto ou pedido você quer que eu consulte?"
)


def ungrounded_amounts(answer: str, evidence: list[str]) -> set[Decimal]:
    allowed: set[Decimal] = set()
    for text in evidence:
        allowed |= money_mentions(text)
    return money_mentions(answer) - allowed


def retry_note(missing: set[Decimal]) -> str:
    values = ", ".join(brl(v) for v in sorted(missing))
    return (
        f"ATENÇÃO: sua última resposta citou valores que não vieram do sistema ({values}). "
        "Use a ferramenta certa (quote para parcelas, totais e frete) ou responda sem esses números."
    )
