"""Grounding guard: amounts, installment plans, protocol numbers and tracking codes in a reply must
come from a tool output or from the customer's own words.

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
_PROTOCOL = re.compile(r"protocolo\D{0,25}?([A-Z]{0,3}-?\d[\d-]{5,})", re.IGNORECASE)
_TRACKING = re.compile(r"\bBR[A-Z0-9]{9}BR\b")


def installment_mentions(text: str) -> set[int]:
    """'12x', '6 x', '10 vezes' -> {12, 6, 10}."""
    return {int(n) for n in _PLAN.findall(text)}


def codes(text: str) -> set[str]:
    """Protocol numbers ('protocolo EM-20260403-001', 'protocolo #2026040301') and tracking codes."""
    return {c.strip("-") for c in _PROTOCOL.findall(text)} | set(_TRACKING.findall(text))


def ungrounded(answer: str, evidence: list[str]) -> list[str]:
    """What the answer states that no piece of evidence contains."""
    money, plans, known = set(), set(), set()
    for text in evidence:
        money |= money_mentions(text)
        plans |= installment_mentions(text)
        known |= codes(text)
    issues = [brl(v) for v in sorted(money_mentions(answer) - money)]
    issues += [f"{n}x" for n in sorted(installment_mentions(answer) - plans)]
    return issues + [f"código {c}" for c in sorted(codes(answer) - known)]


def retry_note(issues: list[str]) -> str:
    return (
        f"ATENÇÃO: sua última resposta citou dados que não vieram do sistema ({', '.join(issues)}). "
        "Use a ferramenta certa (quote para parcelas, totais e frete; create_handoff para gerar protocolo) "
        "ou responda sem esses dados. Nunca invente protocolo."
    )
