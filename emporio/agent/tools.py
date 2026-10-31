"""Tools the model can call. Each one is a thin wrapper: the domain modules do the work and the math.

No `from __future__ import annotations` here on purpose: LangChain reads these signatures at runtime
to build the schemas and to hide the injected `runtime` argument from the model.
"""

import os
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Literal

from langchain.tools import ToolRuntime, tool

from emporio import clock
from emporio.agent.prompts import Session
from emporio.catalog import ROOT, get_store
from emporio.handoff import open_ticket
from emporio.hours import store_status
from emporio.money import brl, money
from emporio.orders import digest, lookup_orders
from emporio.policies import get_policy
from emporio.pricing import build_quote, priced, quote_amount
from emporio.safety import MAX_SUMMARY_CHARS, quote_problem
from emporio.search import search
from emporio.shipping import shipping_for
from emporio.views import handoff_text, orders_text, product_card, quote_text, search_text

PolicyTopic = Literal[
    "contato_e_loja",
    "horario",
    "pagamento",
    "trocas_e_devolucoes",
    "frete_e_entregas",
    "promocoes",
    "atendimento_e_escopo",
    "garantia",
    "privacidade",
]
HandoffReason = Literal[
    "reclamacao",
    "troca_ou_devolucao",
    "garantia",
    "pedido_especial",
    "duvida_de_politica",
    "dados_pessoais",
    "outro",
]


def _money_or_none(value: float | None) -> Decimal | None:
    return None if value is None else money(value)


@tool
def search_products(
    query: str = "",
    category: str = "",
    max_price: float | None = None,
    min_price: float | None = None,
    include_unavailable: bool = False,
) -> str:
    """Search the store catalog by words, category and price range in BRL.

    Use it for any question about which instruments the store has, their prices or availability.
    query: model, brand or features as the customer said them, e.g. "Takamine GD20", "nylon", "eletroacústico".
    category: e.g. "violões", "ukuleles", "guitarras", "baixos", "baterias", "teclados".
    The result shows price, PIX price, active promotion and availability, and lists matching items
    that are not available (sold out, discontinued, coming soon) separately.
    """
    store = get_store()
    result = search(
        store,
        query=query,
        category=category,
        max_price=_money_or_none(max_price),
        min_price=_money_or_none(min_price),
        only_available=not include_unavailable,
    )
    filters = []
    if query:
        filters.append(f'palavras "{query}"')
    if result.category:
        filters.append(f"categoria {result.category.name}")
    if min_price is not None:
        filters.append(f"a partir de {brl(min_price)}")
    if max_price is not None:
        filters.append(f"até {brl(max_price)}")
    filters.append("todos os status" if include_unavailable else "só disponíveis")
    return search_text(store, result, filters)


@tool
def get_product_details(product_id: int) -> str:
    """Full card of one product by its id (#number from search_products): price, PIX, installments,
    specs, availability, past promotions and, when it is unavailable, similar available alternatives."""
    store = get_store()
    product = store.products.get(product_id)
    return product_card(store, product) if product else f"Produto #{product_id} não encontrado no sistema."


@tool
def quote(
    runtime: ToolRuntime[Session],
    product_ids: list[int] | None = None,
    amount: float | None = None,
    installments: int | None = None,
    city: str = "",
) -> str:
    """Price a purchase: total, PIX total, debit/boleto, maximum interest-free installments, a specific
    number of installments if asked, combined payment, and delivery conditions for a city.

    product_ids: ids from search_products; repeat an id to quote more than one unit.
    amount: use only when there is no product, e.g. "em quantas vezes posso parcelar R$ 600?".
    city: delivery city; leave empty to use the city of the identified customer.
    """
    problem = quote_problem(product_ids, amount)
    if problem:
        return problem
    store = get_store()
    customer = store.customer_by_phone(runtime.context.phone if runtime.context else None)
    city = city or (customer.city if customer else "")
    if product_ids:
        unknown = [pid for pid in product_ids if pid not in store.products]
        if unknown:
            return f"Produtos não encontrados no sistema: {', '.join(f'#{pid}' for pid in unknown)}."
        unavailable = [store.products[pid] for pid in set(product_ids) if not store.products[pid].is_available]
        if unavailable:
            names = ", ".join(f"#{p.id} {p.name}" for p in unavailable)
            return f"Não dá para orçar: {names} não está disponível para venda agora."
        counts = Counter(product_ids)
        products = [store.products[pid] for pid in counts]
        result = build_quote([priced(store, p, counts[p.id]) for p in products])
    elif amount:
        products = []
        result = quote_amount(money(amount))
    else:
        return "Informe os produtos (ids) ou um valor para orçar."
    shipping = shipping_for(city, result.subtotal, products)
    return quote_text(result, shipping, city or None, installments)


@tool
def get_my_orders(runtime: ToolRuntime[Session], order_id: int | None = None, email: str = "") -> str:
    """Orders of the customer on this WhatsApp number: status, items, total, tracking, delays and the
    return, exchange and warranty deadlines already computed.

    The number comes from the channel, never from the conversation. If the number is not registered,
    pass the order_id together with the e-mail used in the purchase.
    """
    store = get_store()
    lookup = lookup_orders(
        store,
        phone=runtime.context.phone if runtime.context else None,
        order_id=order_id,
        email=email or None,
    )
    return orders_text(store, lookup, clock.now().date())


@tool
def get_store_policy(topic: PolicyTopic) -> str:
    """Section of the store's policy manual for a topic, plus the store's notes on ambiguous clauses.

    contato_e_loja: address, phone, e-mail, what the store sells. horario: opening hours.
    pagamento: payment methods and installment rules. trocas_e_devolucoes: returns and exchanges.
    frete_e_entregas: delivery and tracking. promocoes: promotion rules. atendimento_e_escopo: tone,
    scope, special situations, complaints. garantia: warranty. privacidade: personal data (LGPD).
    """
    return get_policy(topic)


@tool
def create_handoff(runtime: ToolRuntime[Session], reason: HandoffReason, summary: str) -> str:
    """Open a ticket for the human team and get a protocol number to give the customer.

    Use for complaints, return/exchange/warranty requests, data deletion requests, instruments that are
    not in the system, or when it is unclear how a policy applies.
    summary: order number if there is one, what happened and what the customer wants, in 1-3
    sentences the team can act on. The customer's orders are attached to the ticket automatically.
    """
    store = get_store()
    phone = runtime.context.phone if runtime.context else None
    customer = store.customer_by_phone(phone)
    now = clock.now()
    ticket = open_ticket(
        Path(os.getenv("EMPORIO_VAR_DIR") or ROOT / "var"),
        at=now,
        reason=reason,
        summary=summary[:MAX_SUMMARY_CHARS],
        phone=phone,
        customer=customer.name if customer else None,
        orders=digest(store, customer, now.date()) if customer else None,
    )
    return handoff_text(ticket, store_status(now))


TOOLS = [search_products, get_product_details, quote, get_my_orders, get_store_policy, create_handoff]
