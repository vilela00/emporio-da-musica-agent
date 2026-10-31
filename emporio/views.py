"""Plain-text answers the tools hand to the LLM, in Portuguese (the customer's language).

Every amount the agent may quote is printed here, already computed. The price guard
(emporio/agent/guard.py) only lets through amounts that appeared in a tool output.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from emporio.catalog import Product, Store
from emporio.clock import fmt_date
from emporio.handoff import REASONS, Ticket
from emporio.hours import StoreStatus, describe
from emporio.money import brl
from emporio.orders import STATUS_LABELS, Lookup, deadlines, is_late, payment_label
from emporio.pricing import (
    COMBINED_PAYMENT_ABOVE,
    PricedItem,
    Quote,
    installment_value,
    installments_allowed,
    max_installments,
    min_installment,
    priced,
)
from emporio.search import SearchResult, alternatives
from emporio.shipping import Shipping

AVAILABILITY = {
    "available": "disponível",
    "out_of_stock": "esgotado no momento",
    "discontinued": "descontinuado, não faz mais parte do catálogo",
    "coming_soon": "lançamento em breve, ainda não está à venda",
}

SPEC_LABELS = {
    "top": "tampo",
    "back_sides": "fundo e laterais",
    "neck": "braço",
    "scale": "escala",
    "color": "cor",
    "body": "corpo",
    "shells": "cascos",
    "pieces": "peças",
    "keys": "teclas",
    "polyphony": "polifonia",
}


def specs_text(product: Product) -> str:
    specs = product.specs
    parts = []
    for key, value in specs.items():
        if key == "strings":
            # Same key, two meanings (A-15): string material on acoustic instruments, count on guitars/basses.
            parts.append({"nylon": "cordas de nylon", "steel": "cordas de aço"}.get(value, f"{value} cordas"))
        elif key == "electronics":
            parts.append("com captação (eletroacústico)" if value == "yes" else "sem captação")
        elif key == "hardware":
            parts.append("ferragens incluídas" if value == "included" else f"ferragens: {value}")
        elif key == "type":
            parts.append({"Synthesizer": "sintetizador"}.get(value, value))
        else:
            parts.append(f"{SPEC_LABELS.get(key, key)} {value}")
    return "; ".join(parts)


def price_text(item: PricedItem) -> str:
    if item.promotion:
        promo = item.promotion
        return (
            f"de {brl(item.product.price)} por {brl(item.unit_price)} "
            f"({promo.label}, {promo.percent}% de desconto; o desconto do PIX não acumula)"
        )
    return f"{brl(item.unit_price)} (no PIX: {brl(item.pix_total)})"


def product_line(store: Store, product: Product) -> str:
    category = store.categories[product.category_id].name
    if product.is_available:
        return f"#{product.id} {product.name} | {category} | {price_text(priced(store, product))} | disponível"
    return f"#{product.id} {product.name} | {category} | {AVAILABILITY[product.availability]}"


def product_card(store: Store, product: Product) -> str:
    category = store.categories[product.category_id].name
    lines = [f"#{product.id} {product.name} ({category})"]
    if product.is_available:
        item = priced(store, product)
        stock = "últimas unidades" if product.stock <= 3 else "em estoque"
        lines += [
            f"Situação: disponível, {stock} ({product.stock})",
            f"Preço: {price_text(item)}",
            f"Crédito sem juros: até {_max_plan(item.total)}; débito; boleto (compensação em até 3 dias úteis)",
        ]
    else:
        lines.append(f"Situação: {AVAILABILITY[product.availability]}")
    lines.append(f"Características: {specs_text(product)}")
    if product.description_conflict:
        lines.append(
            "Descrição: não exibida, o cadastro tem informações conflitantes. "
            "Descreva o produto só pelo nome e pelas características."
        )
    else:
        lines.append(f"Descrição: {product.description}")
    past = store.past_promotions(product.id)
    if past:
        listed = ", ".join(f"{p.label} ({p.percent}%)" for p in past)
        lines.append(f"Promoções encerradas, que não valem mais: {listed}")
    if not product.is_available:
        options = alternatives(store, product)
        if options:
            lines.append("Alternativas disponíveis parecidas:")
            lines += [f"- {product_line(store, p)}" for p in options]
    return "\n".join(lines)


def _max_plan(total: Decimal) -> str:
    n = max_installments(total)
    return f"{n}x de {brl(installment_value(total, n))}"


def search_text(store: Store, result: SearchResult, filters: list[str]) -> str:
    lines = [f"Filtros: {' | '.join(filters) if filters else 'nenhum'}"]
    if result.category and not any(
        p.category_id == result.category.id for p in store.products.values()
    ):
        lines.append(f"A categoria {result.category.name} não tem nenhum item cadastrado no sistema agora.")
        return "\n".join(lines)
    if result.relaxed:
        lines.append(
            f"Nenhum item corresponde exatamente às palavras buscadas; mostrando a categoria "
            f"{result.category.name}."
        )
    if not result.shown:
        lines.append("Nenhum produto disponível com esses filtros.")
    else:
        lines.append(f"{result.total} produto(s); mostrando {len(result.shown)}:")
        lines += [f"- {product_line(store, p)}" for p in result.shown]
        if result.total > len(result.shown):
            lines.append(
                f"(+{result.total - len(result.shown)} não exibidos; refine por modelo, tipo de corda ou preço.)"
            )
    if result.unavailable_matches:
        listed = "; ".join(
            f"#{p.id} {p.name} ({AVAILABILITY[p.availability]})" for p in result.unavailable_matches
        )
        lines.append(f"Também correspondem à busca, mas não estão disponíveis: {listed}")
    return "\n".join(lines)


def quote_text(quote: Quote, shipping: Shipping, city: str | None, installments: int | None) -> str:
    lines = ["Orçamento com os preços de hoje:"]
    for item in quote.items:
        lines.append(f"- {item.quantity}x #{item.product.id} {item.product.name}: {price_text(item)}")
    total = quote.subtotal
    lines += [
        f"Total: {brl(total)}",
        f"PIX: {brl(quote.pix_total)} (5% de desconto só sobre itens sem promoção)",
        f"Débito ou boleto: {brl(total)} (boleto compensa em até 3 dias úteis)",
        f"Crédito sem juros: até {_max_plan(total)}",
    ]
    if installments:
        value = installment_value(total, installments)
        if installments_allowed(total, installments):
            lines.append(f"Parcelamento em {installments}x: permitido, {installments}x de {brl(value)}.")
        else:
            lines.append(
                f"Parcelamento em {installments}x: não permitido. A parcela seria {brl(value)}, abaixo do "
                f"mínimo de {brl(min_installment(installments))} para essa faixa (manual §3.1)."
            )
    if quote.combined_payment_allowed:
        lines.append(f"Pagamento combinado (ex.: PIX + cartão): permitido, a compra passa de {brl(COMBINED_PAYMENT_ABOVE)}.")
    else:
        lines.append(f"Pagamento combinado (ex.: PIX + cartão): só para compras acima de {brl(COMBINED_PAYMENT_ABOVE)}.")
    lines.append(shipping_text(shipping, city))
    return "\n".join(lines)


def shipping_text(shipping: Shipping, city: str | None) -> str:
    if shipping.region == "unknown":
        return "Frete: falta a cidade de entrega para eu informar as condições."
    if shipping.region == "metro":
        fee = "grátis (pedido a partir de R$ 500,00)" if shipping.fee == 0 else f"{brl(shipping.fee)} (pedido abaixo de R$ 500,00)"
        return (
            f"Frete para Campo Grande: {fee}; entrega em 1 a 3 dias úteis por motoboy próprio, "
            "com ligação antes da entrega."
        )
    text = (
        f"Frete para {city}: Correios PAC (5 a 12 dias úteis), SEDEX (2 a 5) ou Jadlog (3 a 8), com rastreio "
        "e seguro. O valor depende do CEP, do peso e das dimensões e é calculado no fechamento do pedido."
    )
    if shipping.large_items:
        names = ", ".join(p.name for p in shipping.large_items)
        text += f" Instrumento de grande porte ({names}) pode exigir cotação especial de frete."
    return text


def orders_text(store: Store, lookup: Lookup, today: date) -> str:
    if lookup.message and not lookup.orders:
        return lookup.message
    lines = []
    if lookup.customer:
        lines.append(f"Cliente: {lookup.customer.first_name} ({lookup.customer.city})")
    for order in lookup.orders:
        lines.append("")
        lines.append(f"Pedido #{order.id}, feito em {fmt_date(order.placed_on)}")
        lines.append(f"Situação: {STATUS_LABELS.get(order.status, order.status)}")
        items = ", ".join(
            f"{i.quantity}x {store.products[i.product_id].name}" if i.product_id in store.products
            else f"{i.quantity}x produto #{i.product_id}"
            for i in order.items
        )
        lines.append(f"Itens: {items}")
        lines.append(f"Total do pedido: {brl(order.total)} ({payment_label(order.payment_method)})")
        if order.status == "cancelled" and order.notes:
            lines.append(f"Motivo do cancelamento: {order.notes}")
        if order.tracking_code:
            lines.append(f"Rastreio: {order.tracking_code} (site dos Correios ou da Jadlog)")
        elif order.status in ("pending", "confirmed"):
            lines.append("Ainda não foi despachado; o código de rastreio é enviado por e-mail e WhatsApp no despacho.")
        if order.status == "shipped" and order.estimated_delivery:
            late = " (ATRASADO: a previsão já passou)" if is_late(order, today) else ""
            lines.append(f"Previsão de entrega: {fmt_date(order.estimated_delivery)}{late}")
            if late:
                lines.append(
                    "Se o cliente reclamar do atraso: registre já com create_handoff (motivo reclamacao) "
                    "e informe o protocolo que a ferramenta devolver."
                )
        windows = deadlines(order)
        if windows:
            def state(until: date) -> str:
                return "vigente" if today <= until else "encerrado"

            lines += [
                f"Previsão de entrega: {fmt_date(windows.receipt)} (usada como data de recebimento; "
                "o sistema não registra a entrega real)",
                f"Prazos em {fmt_date(today)}:",
                f"- Arrependimento, 7 dias do recebimento (§4.1): até {fmt_date(windows.withdrawal_until)}, "
                f"{state(windows.withdrawal_until)}",
                f"- Troca por defeito, 30 dias da compra (§4.2): até {fmt_date(windows.defect_exchange_until)}, "
                f"{state(windows.defect_exchange_until)}",
                f"- Garantia legal, 90 dias do recebimento (§8.1): até {fmt_date(windows.legal_warranty_until)}, "
                f"{state(windows.legal_warranty_until)}",
            ]
    return "\n".join(lines).strip()


def handoff_text(ticket: Ticket, status: StoreStatus) -> str:
    sla = (
        "Retorno da equipe em até 24 horas úteis (manual §7.3)."
        if ticket.reason == "reclamacao"
        else "O manual não define prazo para este tipo de pedido: a equipe responde por este WhatsApp "
        "no horário de atendimento. Não prometa dia nem hora."
    )
    return f"Encaminhamento registrado: protocolo {ticket.protocol} ({REASONS[ticket.reason]}). {sla} {describe(status)}"
