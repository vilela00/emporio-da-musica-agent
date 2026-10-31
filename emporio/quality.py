"""Data quality report for the raw CSVs. `python -m emporio.quality` writes docs/data_quality.md.

Nothing here edits data/. The report is the list of things the agent must not repeat to a
customer, and a to-do list for the store team.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from emporio.catalog import ROOT, Store, get_store, normalize
from emporio.money import brl, money
from emporio.pricing import installments_allowed

CAMPAIGN_RANGES = {"Black Friday": (15, 30), "Aniversário da Loja": (10, 25)}  # manual §6.1


@dataclass(frozen=True)
class Finding:
    code: str
    title: str
    evidence: list[str]
    treatment: str


def _items_value(store: Store, order) -> Decimal:
    return money(sum((store.products[i.product_id].price * i.quantity for i in order.items), Decimal(0)))


def findings(store: Store) -> list[Finding]:
    products, orders = store.products, store.orders
    result: list[Finding] = []

    def add(code: str, title: str, evidence: list[str], treatment: str) -> None:
        if evidence:
            result.append(Finding(code, title, evidence, treatment))

    add(
        "A-01",
        "Product name and description mention different brands",
        [
            f"#{p.id} '{p.name}' is described as: \"{p.description[:70]}...\""
            for p in products.values()
            if p.description_conflict
        ],
        "Name, price, stock, status and specs are trusted. "
        "The description is hidden from the model for these products.",
    )
    sold = defaultdict(list)
    for order in orders.values():
        for item in order.items:
            sold[item.product_id].append(f"#{order.id} ({order.status})")
    add(
        "A-02",
        "Product marked 'coming_soon' was already sold",
        [f"#{p.id} '{p.name}' is coming_soon, stock {p.stock}, sold in orders {', '.join(sold[p.id])}"
         for p in products.values() if p.status == "coming_soon" and sold[p.id]],
        "Status wins for new sales ('launching soon, not on sale yet'). Existing orders stay valid.",
    )
    add(
        "A-03",
        "Discontinued product still has stock",
        [
            f"#{p.id} '{p.name}': discontinued with {p.stock} units"
            for p in products.values()
            if p.status == "discontinued" and p.stock > 0
        ],
        "Treated as out of the catalog (manual §7.3), with equivalents offered. "
        "Leftover stock is flagged to the team here.",
    )
    add(
        "A-04",
        "Active product with zero stock",
        [f"#{p.id} '{p.name}'" for p in products.values() if p.status == "active" and p.stock == 0],
        "Reported as temporarily unavailable, with similar available alternatives (manual §7.3).",
    )
    add(
        "A-05",
        "Order total differs from its items at current prices (order_items has no unit price)",
        [f"order #{o.id}: total {brl(o.total)}, items at today's prices {brl(_items_value(store, o))}"
         for o in orders.values() if o.total != _items_value(store, o)],
        "The order total is what the customer paid; current prices never recompute a past order.",
    )
    violations = []
    for o in orders.values():
        match = re.fullmatch(r"credit_(\d+)x", o.payment_method)
        if match and not installments_allowed(o.total, int(match.group(1))):
            n = int(match.group(1))
            violations.append(f"order #{o.id}: {n}x of {brl(o.total / n)} for {brl(o.total)}")
    add(
        "A-06",
        "Installment plans below the manual's minimum (§3.1)",
        violations,
        "Historical, not shown to customers. Every new quote enforces §3.1.",
    )
    add(
        "A-07",
        "PIX orders without the 5% discount",
        [f"order #{o.id}: {brl(o.total)} by PIX, list price {brl(_items_value(store, o))}"
         for o in orders.values() if o.payment_method == "pix" and o.total == _items_value(store, o)],
        "Historical (prices or conditions of the time), not shown to customers.",
    )
    by_email = defaultdict(list)
    by_first = defaultdict(list)
    for c in store.customers.values():
        by_email[c.email.lower()].append(c)
        by_first[normalize(c.first_name)].append(c)
    evidence = [
        f"{email} is shared by " + " and ".join(f"#{c.id} '{c.name}'" for c in group)
        for email, group in by_email.items() if len(group) > 1
    ]
    namesakes = sum(1 for group in by_first.values() if len(group) > 1)
    if evidence:
        evidence.append(
            f"{namesakes} first names are shared by two or three customers "
            "(e.g. three Brunos, three Thiagos, three Camilas)"
        )
    add(
        "A-08",
        "Customer records that a name lookup would mix up",
        evidence,
        "Customers are identified by the WhatsApp number, never by name. "
        "E-mail is only a second check, together with the order number.",
    )
    used = {p.category_id for p in products.values()}
    add(
        "A-12",
        "Categories with no products (the manual promises '300+ instruments'; the data has "
        f"{len(products)})",
        [f"#{c.id} {c.name}" for c in store.categories.values() if c.id not in used],
        "The agent says it found nothing in the system right now and offers to check with the team. "
        "It never says the store does not sell it.",
    )
    by_product = defaultdict(list)
    for promo in store.promotions:
        by_product[promo.product_id].append(promo)
    promo_evidence = [
        f"product #{pid} has {len(group)} promotions: " + ", ".join(f"#{p.id} {p.label} {p.percent}%" for p in group)
        for pid, group in by_product.items() if len(group) > 1
    ]
    for promo in store.promotions:
        low, high = CAMPAIGN_RANGES.get(promo.label, (0, 100))
        if not low <= promo.percent <= high:
            promo_evidence.append(
                f"promotion #{promo.id} '{promo.label}' gives {promo.percent}%, outside the manual's {low}-{high}%"
            )
    active = sum(p.active for p in store.promotions)
    promo_evidence.append(f"only {active} of {len(store.promotions)} promotions are active, and none has dates")
    add(
        "A-13",
        "Promotions: no dates, duplicates per product, campaigns outside the manual's ranges",
        promo_evidence,
        "Only is_active decides. If two were active on one product, the larger discount would win (they don't stack).",
    )
    schemas = defaultdict(set)
    for p in products.values():
        schemas[store.categories[p.category_id].name].add(", ".join(sorted(p.specs)))
    add(
        "A-15",
        "Specs change shape by category and 'strings' has two meanings",
        [f"{name}: {' / '.join(sorted(keys))}" for name, keys in schemas.items()]
        + [
            "'strings' is the material (nylon/steel) on Violões and Ukuleles, "
            "and the count ('4', '6') on Guitarras and Baixos"
        ],
        "Specs are rendered with category-aware labels in Portuguese.",
    )
    last_day = max(o.placed_on for o in orders.values())
    add(
        "A-16",
        f"Shipped order past its estimated delivery (dataset ends on {last_day.isoformat()})",
        [
            f"order #{o.id}: shipped, estimated {o.estimated_delivery.isoformat()}"
            for o in orders.values()
            if o.status == "shipped" and o.estimated_delivery and o.estimated_delivery < last_day
        ],
        "The order tool flags the delay; the agent offers the tracking code and a handoff.",
    )
    add(
        "A-17",
        "order_items has no unit price",
        ["columns: order_id, quantity, product_id"],
        "Orders show items and the order total, never a per-item price.",
    )
    return result


def report(store: Store) -> str:
    rows = findings(store)
    lines = [
        "# Data quality report",
        "",
        "Generated by `python -m emporio.quality` from the raw CSVs in `data/` (never edited).",
        "Codes match the assumptions table in the README.",
        "",
        "| Code | Finding | Treatment |",
        "|---|---|---|",
    ]
    lines += [f"| {f.code} | {f.title} | {f.treatment} |" for f in rows]
    for f in rows:
        lines += ["", f"## {f.code}: {f.title}", ""]
        lines += [f"- {e}" for e in f.evidence]
    return "\n".join(lines) + "\n"


def main() -> None:
    target = ROOT / "docs" / "data_quality.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text(report(get_store()), encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
