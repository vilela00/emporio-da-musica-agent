from emporio.catalog import brand_conflict, normalize, phone_digits


def test_loads_every_row(store):
    assert len(store.products) == 65
    assert len(store.customers) == 50
    assert len(store.orders) == 20
    assert sum(len(o.items) for o in store.orders.values()) == 22


def test_availability(store):
    assert store.products[95].availability == "available"
    assert store.products[96].availability == "out_of_stock"
    assert store.products[113].availability == "discontinued"
    assert store.products[136].availability == "discontinued"  # 13 units, still out of the catalog
    assert store.products[130].availability == "coming_soon"


def test_brand_conflicts_flagged(store):
    assert brand_conflict("Music Man Bass 1X Electric Bass", "Contrabaixo elétrico Fender Jazz Bass")
    assert not brand_conflict("Music Man Bass 4X Electric Bass", "Contrabaixo elétrico Music Man StingRay")
    flagged = {p.id for p in store.products.values() if p.description_conflict}
    assert flagged == {135, 137, 139, 140, 142, 144}


def test_customer_by_phone_accepts_any_format(store):
    assert store.customer_by_phone("+55 67 99789-0123").id == 14
    assert store.customer_by_phone("(67) 99789-0123").id == 14
    assert store.customer_by_phone("67 0000-0000") is None
    assert phone_digits("+55 (67) 99812-3456") == "67998123456"


def test_active_promotion_and_history(store):
    assert store.active_promotion(90).percent == 18
    assert store.active_promotion(95) is None
    assert [p.percent for p in store.past_promotions(95)] == [12]


def test_normalize():
    assert normalize("Violão Aço 7-Cordas") == "violao aco 7 cordas"
