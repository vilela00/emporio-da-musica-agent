"""Grounding guard: what a reply states as fact must come from the system.

Amounts must appear in a tool output: a price the customer typed confirms nothing ("the salesman said
R$ 5.000, right?"). Installment plans, protocol numbers, tracking codes, phone numbers and e-mails may
also come from the customer's own messages (the plan they asked about, their order, their e-mail).

Manual §7.1: never give prices, stock or deadlines without checking the system; a wrong price can
count as misleading advertising. The prompt asks for that; this check enforces it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from decimal import Decimal

from emporio.money import brl, money_mentions

FALLBACK = (
    "Quero te passar a informação certinha e não consegui confirmar tudo no sistema agora. "
    "Me diz de novo o que você precisa? Se preferir, passo para a equipe."
)

_PLAN = re.compile(r"\b(\d{1,2})\s?(?:x|vezes)\b", re.IGNORECASE)
_PLAN_VALUE = re.compile(r"\b(\d{1,2})\s?x\s+de\s+(R\$\s?[\d.]+,\d{2})", re.IGNORECASE)
_PROTOCOL = re.compile(r"protocolo\D{0,25}?([A-Z]{0,3}-?\d[\d-]{5,})", re.IGNORECASE)
_TICKET = re.compile(r"\bEM-\d{8}-\d{3}\b")
_TRACKING = re.compile(r"\bBR[A-Z0-9]{9}BR\b")
_PHONE = re.compile(r"(?<![\d-])(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}-\d{4}(?![\d-])")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def installment_mentions(text: str) -> set[int]:
    """'12x', '6 x', '10 vezes' -> {12, 6, 10}. '1x' is paying at once, not a plan."""
    return {int(n) for n in _PLAN.findall(text)} - {1}


def plan_values(text: str) -> set[tuple[int, Decimal]]:
    """'4x de R$ 87,48' -> {(4, 87.48)}: a count and a value that are only true together."""
    pairs = set()
    for count, value in _PLAN_VALUE.findall(text):
        pairs |= {(int(count), amount) for amount in money_mentions(value)}
    return pairs


def codes(text: str) -> set[str]:
    """Protocol numbers ('protocolo EM-20260403-001', 'protocolo #2026040301', a bare 'EM-20260403-002')
    and tracking codes. A phone number right after the word 'protocolo' is still a phone number."""
    protocols = {c.strip("-") for c in _PROTOCOL.findall(text)}
    protocols = {c for c in protocols if not _PHONE.fullmatch(c)}
    return protocols | set(_TICKET.findall(text)) | set(_TRACKING.findall(text))


def phones(text: str) -> dict[str, str]:
    """Phone numbers keyed by their last 8 digits, so '(67) 3341-4444' and '3341-4444' are the same."""
    return {re.sub(r"\D", "", p)[-8:]: p.strip() for p in _PHONE.findall(text)}


def emails(text: str) -> set[str]:
    return {e.lower() for e in _EMAIL.findall(text)}


def ungrounded(answer: str, tools: Sequence[str], said: Sequence[str] = ()) -> list[str]:
    """What the answer states that no tool output contains (or, except amounts, no customer message)."""
    money, pairs, plans, known, numbers, addresses = set(), set(), set(), set(), set(), set()
    for text in tools:
        money |= money_mentions(text)
        pairs |= plan_values(text)
    for text in [*tools, *said]:
        plans |= installment_mentions(text)
        known |= codes(text)
        numbers |= phones(text).keys()
        addresses |= emails(text)
    issues = [brl(v) for v in sorted(money_mentions(answer) - money)]
    issues += [f"{n}x" for n in sorted(installment_mentions(answer) - plans)]
    # each part grounded on its own, but not printed together by any tool ("6x de R$ 87,48")
    issues += [f"{n}x de {brl(v)}" for n, v in sorted(plan_values(answer) - pairs) if v in money and n in plans]
    issues += [f"código {c}" for c in sorted(codes(answer) - known)]
    issues += [f"telefone {shown}" for tail, shown in sorted(phones(answer).items()) if tail not in numbers]
    return issues + [f"e-mail {e}" for e in sorted(emails(answer) - addresses)]


def retry_note(issues: list[str]) -> str:
    return (
        f"ATENÇÃO: sua última resposta citou dados que não vieram do sistema ({', '.join(issues)}). "
        "Valor dito pelo cliente não confirma preço. Use a ferramenta certa (quote para parcelas, totais "
        "e frete; get_store_policy para o contato da loja; create_handoff para gerar protocolo) ou responda "
        "sem esses dados. Nunca invente protocolo, telefone ou e-mail."
    )
