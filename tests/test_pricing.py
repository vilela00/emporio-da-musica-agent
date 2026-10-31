from decimal import Decimal

from emporio.pricing import build_quote, installments_allowed, max_installments, priced, quote_amount


def test_installment_tiers_follow_section_3_1():
    assert max_installments(Decimal("349.90")) == 4    # 4x 87,48 ok; 5x 69,98 < 80
    assert max_installments(Decimal("159.90")) == 3    # 3x 53,30 ok; 4x 39,98 < 80
    assert max_installments(Decimal("459.90")) == 5
    assert max_installments(Decimal("1000.00")) == 10  # 10x of exactly R$ 100,00 is allowed
    assert max_installments(Decimal("2199.00")) == 12
    assert max_installments(Decimal("90.00")) == 1     # 2x would be R$ 45,00 < 50
    assert not installments_allowed(Decimal("349.90"), 6)


def test_promotion_price_and_no_pix_on_top(store):
    item = priced(store, store.products[90])
    assert item.unit_price == Decimal("1967.18")
    assert item.pix_total == Decimal("1967.18")


def test_pix_discount_on_list_price(store):
    assert priced(store, store.products[95]).pix_total == Decimal("2089.05")


def test_mixed_cart_applies_pix_only_to_regular_items(store):
    quote = build_quote([priced(store, store.products[90]), priced(store, store.products[81])])
    assert quote.subtotal == Decimal("2567.08")          # 1967,18 + 599,90
    assert quote.pix_total == Decimal("2537.09")         # 1967,18 + 569,91
    assert quote.combined_payment_allowed


def test_combined_payment_only_above_2000():
    assert not quote_amount(Decimal("2000.00")).combined_payment_allowed
    assert quote_amount(Decimal("2000.01")).combined_payment_allowed
