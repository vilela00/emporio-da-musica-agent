"""Grounding guard: every amount and installment plan in a reply must come from a tool output or
from the customer's own words.

Manual §7.1: never give prices, stock or deadlines without checking the system; a wrong price can
count as misleading advertising. The prompt asks for that; this check enforces it.
"""

from __future__ import annotations

import re

from emporio.money import brl, money_mentions

FALLBACK = (
    "Quero te passar os valores certinhos, então deixa eu conferir no sistema antes. "
    "Me confirma qual produto ou pedido você quer que eu consulte?"
)

_PLAN = re.compile(r"\b(\d{1,2})\s?(?:x|vezes)\b", re.IGNORECASE)


def installment_mentions(text: str) -> set[int]:
    """'12x', '6 x', '10 vezes' -> {12, 6, 10}."""
    return {int(n) for n in _PLAN.findall(text)}


def ungrounded(answer: str, evidence: list[str]) -> list[str]:
    """Amounts and installment plans in the answer that no piece of evidence contains."""
    money, plans = set(), set()
    for text in evidence:
        money |= money_mentions(text)
        plans |= installment_mentions(text)
    issues = [brl(v) for v in sorted(money_mentions(answer) - money)]
    return issues + [f"{n}x" for n in sorted(installment_mentions(answer) - plans)]


def retry_note(issues: list[str]) -> str:
    return (
        f"ATENÇÃO: sua última resposta citou valores ou parcelamentos que não vieram do sistema "
        f"({', '.join(issues)}). Use a ferramenta certa (quote para parcelas, totais e frete) ou "
        "responda sem esses números."
    )
