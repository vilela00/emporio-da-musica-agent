from decimal import Decimal

from emporio.shipping import shipping_for


def test_campo_grande_free_from_500(store):
    assert shipping_for("Campo Grande", Decimal("500.00"), []).fee == 0
    assert shipping_for("campo grande", Decimal("499.99"), []).fee == Decimal("35.00")


def test_other_cities_and_large_items(store):
    drum = store.products[139]
    result = shipping_for("Dourados", Decimal("4439"), [drum])
    assert result.region == "other" and result.fee is None and result.large_items == (drum,)


def test_unknown_city():
    assert shipping_for(None, Decimal(100), []).region == "unknown"
