from datetime import date
from decimal import Decimal

from emporio.money import money_mentions
from emporio.orders import lookup_orders
from emporio.pricing import build_quote, priced
from emporio.shipping import shipping_for
from emporio.views import orders_text, product_card, quote_text


def test_product_card_prices_and_past_promotion(store):
    card = product_card(store, store.products[95])
    assert "R$ 2.199,00 (no PIX: R$ 2.089,05)" in card
    assert "12x de R$ 183,25" in card
    assert "Promoções encerradas, que não valem mais: Oferta Especial (12%)" in card


def test_conflicting_description_is_hidden(store):
    card = product_card(store, store.products[135])
    assert "Fender" not in card and "não exibida" in card


def test_out_of_stock_card_offers_alternatives(store):
    card = product_card(store, store.products[96])
    assert "esgotado" in card and "Alternativas disponíveis" in card and "R$ 799,90" not in card


def test_quote_refuses_installments_below_minimum(store):
    quote = build_quote([priced(store, store.products[120])])
    text = quote_text(quote, shipping_for("Campo Grande", quote.subtotal, []), "Campo Grande", 6)
    assert "6x: não permitido" in text and "R$ 80,00" in text
    assert "Frete para Campo Grande: R$ 35,00" in text


def test_order_text_has_deadlines(store):
    text = orders_text(store, lookup_orders(store, phone="(67) 99789-0123"), date(2026, 3, 23))
    assert "até 24/02/2026, encerrado" in text and "até 18/05/2026, vigente" in text
    assert Decimal("159.90") in money_mentions(text)


def test_late_order_tells_the_model_to_register_the_complaint(store):
    text = orders_text(store, lookup_orders(store, phone="+55 67 99654-7821"), date(2026, 4, 3))
    assert "ATRASADO" in text and "create_handoff" in text


def test_quote_explains_plans_outside_1_to_12(store):
    quote = build_quote([priced(store, store.products[95])])
    text = quote_text(quote, shipping_for("Campo Grande", quote.subtotal, []), "Campo Grande", 18)
    assert "18x: não existe" in text and "1x a 12x" in text and "abaixo do mínimo" not in text
