"""Delivery rules (manual §5)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from emporio.catalog import Product, normalize

# The manual does not list the metropolitan municipalities; only the capital is assumed (A-25).
METRO_CITIES = {"campo grande"}
FREE_SHIPPING_FROM = Decimal("500.00")  # 'acima de' / 'abaixo de' R$ 500 leaves 500,00 open: free (A-11)
METRO_FEE = Decimal("35.00")
LARGE_CATEGORIES = {2, 3}  # basses (contrabaixos) and acoustic drum kits, manual §5.2


@dataclass(frozen=True)
class Shipping:
    region: str  # metro | other | unknown
    fee: Decimal | None
    large_items: tuple[Product, ...] = ()


def is_large(product: Product) -> bool:
    return product.category_id in LARGE_CATEGORIES or "piano" in normalize(product.name)


def city_key(city: str) -> str:
    """'Campo Grande/MS', 'Campo Grande - MS', 'campo grande, ms' -> 'campo grande'."""
    key = normalize(city)
    return key.removesuffix(" ms") if key.endswith(" ms") else key


def shipping_for(city: str | None, subtotal: Decimal, products: list[Product]) -> Shipping:
    if not city:
        return Shipping("unknown", None)
    if city_key(city) in METRO_CITIES:
        return Shipping("metro", Decimal(0) if subtotal >= FREE_SHIPPING_FROM else METRO_FEE)
    return Shipping("other", None, tuple(p for p in products if is_large(p)))
