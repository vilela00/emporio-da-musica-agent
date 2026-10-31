"""Money in BRL: Decimal arithmetic, Brazilian formatting and detection of amounts in free text."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")

_NUMBER = r"\d{1,3}(?:\.\d{3})+|\d+"
_WITH_CENTS = re.compile(rf"(?<![\d.,])({_NUMBER}),(\d{{2}})(?!\d)")
_PREFIXED = re.compile(rf"R\$\s*({_NUMBER})(,\d{{2}})?(?![\d.,]\d)")


def money(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def brl(value: str | int | float | Decimal) -> str:
    """Format as R$ 2.199,00."""
    text = f"{money(value):,.2f}"
    return "R$ " + text.replace(",", "_").replace(".", ",").replace("_", ".")


def money_mentions(text: str) -> set[Decimal]:
    """Every amount written in the text: 'R$ 2.199,00', 'R$1000', '183,25'."""
    found = {money(whole.replace(".", "") + "." + cents) for whole, cents in _WITH_CENTS.findall(text)}
    for whole, cents in _PREFIXED.findall(text):
        if not cents:
            found.add(money(whole.replace(".", "")))
    return found
