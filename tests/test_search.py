from decimal import Decimal

from emporio.search import alternatives, resolve_category, search


def test_violoes_up_to_1000(store):
    result = search(store, category="violões", max_price=Decimal(1000), limit=20)
    assert {p.id for p in result.shown} == {83, 85, 89, 88, 81, 84, 87, 86, 107, 82, 91, 112}
    assert [p.id for p in result.shown][:2] == [83, 85]  # cheapest first
    assert {p.id for p in result.unavailable_matches} == {96, 113}


def test_model_name_lookup_with_typo_and_spacing(store):
    assert search(store, query="Takamine GD20").shown[0].id == 95
    assert search(store, query="takamini gd 20").shown[0].id == 95


def test_out_of_stock_item_is_reported_not_hidden(store):
    result = search(store, query="Giannini GF-3D")
    assert 96 in {p.id for p in result.unavailable_matches}


def test_category_from_query_and_empty_category(store):
    result = search(store, query="saxofone")
    assert result.category.id == 6 and result.shown == []


def test_nylon_for_beginners(store):
    result = search(store, query="nylon iniciante", category="violão", limit=20)
    assert result.shown and all(p.specs["strings"] == "nylon" for p in result.shown)


def test_relaxed_when_words_match_nothing_in_category(store):
    result = search(store, query="piano digital")
    assert result.relaxed and result.category.id == 4 and result.shown


def test_alternatives_keep_string_type_and_price_range(store):
    options = alternatives(store, store.products[96])
    assert len(options) == 3
    assert all(p.is_available and p.specs["strings"] == "steel" for p in options)


def test_resolve_category_words(store):
    assert resolve_category(store, "ukulele").id == 9
    assert resolve_category(store, "contrabaixo").id == 2
    assert resolve_category(store, "Teclados e Pianos").id == 4
