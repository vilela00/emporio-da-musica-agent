"""Typed, read-only view of the store CSVs.

The raw files in data/ are never edited. Conflicts found while loading are flagged on the
records (see docs/data_quality.md) so the agent never repeats them to a customer.
"""

from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from emporio.money import money

ROOT = Path(__file__).resolve().parent.parent
FILE_PATTERN = "desafio_tecnico_ai_eng - {table}.csv"

BRANDS = (
    "Yamaha", "Tagima", "Giannini", "Rozini", "Shelby", "Crafter", "Martin", "Taylor",
    "Takamine", "Kala", "Ohana", "Kalani", "Fender", "Gibson", "Ibanez", "PRS",
    "Music Man", "Pearl", "Tama", "Korg", "Nord", "Roland",
)  # fmt: skip


def normalize(text: str) -> str:
    """Lowercase, accents removed, punctuation turned into single spaces."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).split())


def phone_digits(phone: str) -> str:
    """'+55 (67) 99812-3456' -> '67998123456'."""
    digits = re.sub(r"\D", "", phone or "")
    return digits[2:] if len(digits) > 11 and digits.startswith("55") else digits


def brands_in(text: str) -> set[str]:
    return {b for b in BRANDS if re.search(rf"\b{re.escape(b)}\b", text, re.IGNORECASE)}


def brand_conflict(name: str, description: str) -> bool:
    """True when the description names another brand than the product name (A-01)."""
    in_name, in_description = brands_in(name), brands_in(description)
    return bool(in_name and in_description and not in_name & in_description)


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    description: str


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    category_id: int
    price: Decimal
    description: str
    stock: int
    status: str  # active | discontinued | coming_soon
    specs: dict[str, str]
    created_at: date
    description_conflict: bool

    @property
    def availability(self) -> str:
        if self.status in ("discontinued", "coming_soon"):
            return self.status
        return "available" if self.stock > 0 else "out_of_stock"

    @property
    def is_available(self) -> bool:
        return self.availability == "available"


@dataclass(frozen=True)
class Promotion:
    id: int
    product_id: int
    percent: int
    label: str
    active: bool


@dataclass(frozen=True)
class Customer:
    id: int
    name: str
    phone: str
    email: str
    city: str

    @property
    def first_name(self) -> str:
        return self.name.split()[0]


@dataclass(frozen=True)
class OrderItem:
    product_id: int
    quantity: int


@dataclass(frozen=True)
class Order:
    id: int
    customer_id: int
    placed_on: date
    status: str  # pending | confirmed | shipped | delivered | cancelled
    total: Decimal
    payment_method: str
    tracking_code: str | None
    estimated_delivery: date | None
    notes: str | None
    items: tuple[OrderItem, ...]


@dataclass(frozen=True)
class Store:
    categories: dict[int, Category]
    products: dict[int, Product]
    promotions: tuple[Promotion, ...]
    customers: dict[int, Customer]
    orders: dict[int, Order]

    @classmethod
    def load(cls, data_dir: Path) -> Store:
        def rows(table: str) -> list[dict[str, str]]:
            path = data_dir / FILE_PATTERN.format(table=table)
            with path.open(encoding="utf-8-sig", newline="") as handle:
                return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]

        categories = {
            int(r["category_id"]): Category(int(r["category_id"]), r["name"], r["description"])
            for r in rows("categories")
        }
        products = {
            int(r["product_id"]): Product(
                id=int(r["product_id"]),
                name=r["name"],
                category_id=int(r["category_id"]),
                price=money(r["price_brl"]),
                description=r["description"],
                stock=int(r["stock_quantity"]),
                status=r["status"],
                specs={k: str(v) for k, v in json.loads(r["specs"]).items()},
                created_at=date.fromisoformat(r["created_at"]),
                description_conflict=brand_conflict(r["name"], r["description"]),
            )
            for r in rows("products")
        }
        promotions = tuple(
            Promotion(
                int(r["promotion_id"]), int(r["product_id"]), int(r["discount_percent"]),
                r["description"], r["is_active"] == "1",
            )
            for r in rows("promotions")
        )
        customers = {
            int(r["customer_id"]): Customer(
                int(r["customer_id"]), r["name"], r["phone"], r["email"], r["city"]
            )
            for r in rows("customers")
        }
        items: dict[int, list[OrderItem]] = {}
        for r in rows("order_items"):
            items.setdefault(int(r["order_id"]), []).append(
                OrderItem(int(r["product_id"]), int(r["quantity"]))
            )
        orders = {
            int(r["order_id"]): Order(
                id=int(r["order_id"]),
                customer_id=int(r["customer_id"]),
                placed_on=date.fromisoformat(r["order_date"]),
                status=r["status"],
                total=money(r["total_brl"]),
                payment_method=r["payment_method"],
                tracking_code=r["tracking_code"] or None,
                estimated_delivery=date.fromisoformat(r["estimated_delivery"])
                if r["estimated_delivery"]
                else None,
                notes=r["notes"] or None,
                items=tuple(items.get(int(r["order_id"]), ())),
            )
            for r in rows("orders")
        }
        return cls(categories, products, promotions, customers, orders)

    def active_promotion(self, product_id: int) -> Promotion | None:
        """Promotions don't stack (manual §6.2); if two were active, the larger discount wins."""
        active = [p for p in self.promotions if p.product_id == product_id and p.active]
        return max(active, key=lambda p: p.percent, default=None)

    def past_promotions(self, product_id: int) -> list[Promotion]:
        return [p for p in self.promotions if p.product_id == product_id and not p.active]

    def customer_by_phone(self, phone: str | None) -> Customer | None:
        digits = phone_digits(phone or "")
        if not digits:
            return None
        return next((c for c in self.customers.values() if phone_digits(c.phone) == digits), None)

    def orders_of(self, customer_id: int) -> list[Order]:
        mine = [o for o in self.orders.values() if o.customer_id == customer_id]
        return sorted(mine, key=lambda o: o.placed_on, reverse=True)


@lru_cache(maxsize=1)
def get_store() -> Store:
    return Store.load(Path(os.getenv("EMPORIO_DATA_DIR", ROOT / "data")))
