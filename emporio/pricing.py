"""Prices and payment conditions (manual §3 and §6.2), computed here and never by the LLM."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from emporio.catalog import Product, Promotion, Store
from emporio.money import money

PIX_DISCOUNT = Decimal("0.05")
COMBINED_PAYMENT_ABOVE = Decimal("2000.00")
MAX_INSTALLMENTS = 12


def min_installment(n: int) -> Decimal:
    """Manual §3.1. It is more specific than the 'R$ 100 minimum' in the §3 table, so it wins (A-10)."""
    if n == 1:
        return Decimal(0)
    if n <= 3:
        return Decimal(50)
    if n <= 6:
        return Decimal(80)
    return Decimal(100)


def installments_allowed(total: Decimal, n: int) -> bool:
    return 1 <= n <= MAX_INSTALLMENTS and (n == 1 or total / n >= min_installment(n))


def max_installments(total: Decimal) -> int:
    return max(n for n in range(1, MAX_INSTALLMENTS + 1) if installments_allowed(total, n))


def installment_value(total: Decimal, n: int) -> Decimal:
    return money(total / n)


@dataclass(frozen=True)
class PricedItem:
    product: Product
    quantity: int
    promotion: Promotion | None

    @property
    def unit_price(self) -> Decimal:
        if self.promotion is None:
            return self.product.price
        return money(self.product.price * (100 - self.promotion.percent) / 100)

    @property
    def total(self) -> Decimal:
        return money(self.unit_price * self.quantity)

    @property
    def pix_total(self) -> Decimal:
        """PIX takes 5% off list prices only; it does not stack on a promotional price."""
        return self.total if self.promotion else money(self.total * (1 - PIX_DISCOUNT))


def priced(store: Store, product: Product, quantity: int = 1) -> PricedItem:
    return PricedItem(product, quantity, store.active_promotion(product.id))


@dataclass(frozen=True)
class Quote:
    items: tuple[PricedItem, ...]
    subtotal: Decimal
    pix_total: Decimal

    @property
    def max_installments(self) -> int:
        return max_installments(self.subtotal)

    @property
    def combined_payment_allowed(self) -> bool:
        return self.subtotal > COMBINED_PAYMENT_ABOVE


def build_quote(items: list[PricedItem]) -> Quote:
    subtotal = money(sum((i.total for i in items), Decimal(0)))
    pix_total = money(sum((i.pix_total for i in items), Decimal(0)))
    return Quote(tuple(items), subtotal, pix_total)


def quote_amount(amount: Decimal) -> Quote:
    """A quote for a bare amount (no product): assumes list prices, so PIX applies."""
    amount = money(amount)
    return Quote((), amount, money(amount * (1 - PIX_DISCOUNT)))
