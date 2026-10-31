"""Order lookup scoped to the customer on the line, plus return and warranty deadlines.

Identity comes from the channel (the WhatsApp number), never from a name typed in the chat:
the base has namesakes and two records sharing one e-mail (A-08).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from emporio.catalog import Customer, Order, Store
from emporio.clock import fmt_date

STATUS_LABELS = {
    "pending": "pendente (aguardando confirmação)",
    "confirmed": "confirmado (em preparação para envio)",
    "shipped": "enviado",
    "delivered": "entregue",
    "cancelled": "cancelado",
}

NOT_CONFIRMED = "Não consegui confirmar esse pedido com o e-mail informado."


def payment_label(method: str) -> str:
    if method.startswith("credit_"):
        return f"cartão de crédito em {method.removeprefix('credit_')}"
    return {"pix": "PIX", "debit": "cartão de débito", "boleto": "boleto bancário"}.get(method, method)


@dataclass(frozen=True)
class Deadlines:
    """Manual §4.1 (7 days from receipt), §4.2 (30 days from purchase), §8.1 (90 days from receipt).

    The data has no actual receipt date, so the estimated delivery date stands in for it (A-14).
    """

    receipt: date
    withdrawal_until: date
    defect_exchange_until: date
    legal_warranty_until: date


def deadlines(order: Order) -> Deadlines | None:
    if order.status != "delivered" or order.estimated_delivery is None:
        return None
    receipt = order.estimated_delivery
    return Deadlines(
        receipt=receipt,
        withdrawal_until=receipt + timedelta(days=7),
        defect_exchange_until=order.placed_on + timedelta(days=30),
        legal_warranty_until=receipt + timedelta(days=90),
    )


def is_late(order: Order, today: date) -> bool:
    return (
        order.status == "shipped"
        and order.estimated_delivery is not None
        and order.estimated_delivery < today
    )


@dataclass(frozen=True)
class Lookup:
    customer: Customer | None
    orders: list[Order]
    message: str | None = None


def lookup_orders(
    store: Store, *, phone: str | None, order_id: int | None = None, email: str | None = None
) -> Lookup:
    customer = store.customer_by_phone(phone)
    if customer:
        mine = store.orders_of(customer.id)
        if order_id is not None:
            mine = [o for o in mine if o.id == order_id]
            if not mine:
                return Lookup(customer, [], f"O pedido #{order_id} não está entre os pedidos deste número.")
        return Lookup(customer, mine, None if mine else "Não há pedidos registrados para este número.")

    if order_id is None or not email:
        return Lookup(
            None,
            [],
            "Este número não está no cadastro. Para consultar um pedido, preciso do número do pedido "
            "e do e-mail usado na compra.",
        )
    order = store.orders.get(order_id)
    owner = store.customers.get(order.customer_id) if order else None
    if order is None or owner is None or owner.email.lower() != email.strip().lower():
        return Lookup(None, [], NOT_CONFIRMED)  # same answer for 'no such order': no enumeration
    return Lookup(owner, [order])


def digest(store: Store, customer: Customer, today: date) -> str:
    """One line per order, attached to handoff tickets so the team does not have to look them up."""
    lines = []
    for order in store.orders_of(customer.id):
        bits = [f"#{order.id} {order.status}", f"total {order.total}"]
        if order.tracking_code:
            bits.append(f"rastreio {order.tracking_code}")
        if order.estimated_delivery:
            late = " (atrasado)" if is_late(order, today) else ""
            bits.append(f"previsão {fmt_date(order.estimated_delivery)}{late}")
        lines.append(", ".join(bits))
    return "; ".join(lines) or "sem pedidos"
