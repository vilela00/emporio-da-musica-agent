from datetime import date

from emporio.orders import NOT_CONFIRMED, deadlines, is_late, lookup_orders

LETICIA = "(67) 99789-0123"   # customer 14, order 7
ANA = "+55 67 99654-7821"     # customer 2, order 8


def test_customer_sees_only_her_orders(store):
    found = lookup_orders(store, phone=LETICIA)
    assert [o.id for o in found.orders] == [7]
    blocked = lookup_orders(store, phone=LETICIA, order_id=8)
    assert blocked.orders == [] and "não está entre os pedidos" in blocked.message


def test_unknown_number_needs_order_and_email(store):
    assert lookup_orders(store, phone="(67) 90000-0000", order_id=8).orders == []
    ok = lookup_orders(store, phone="(67) 90000-0000", order_id=8, email="anacarol.ferreira@coldmail.com")
    assert [o.id for o in ok.orders] == [8]


def test_wrong_email_and_missing_order_look_the_same(store):
    wrong = lookup_orders(store, phone=None, order_id=8, email="someone@else.com")
    missing = lookup_orders(store, phone=None, order_id=999, email="someone@else.com")
    assert wrong.message == missing.message == NOT_CONFIRMED


def test_return_and_warranty_deadlines(store):
    windows = deadlines(store.orders[7])
    assert windows.withdrawal_until == date(2026, 2, 24)
    assert windows.defect_exchange_until == date(2026, 3, 5)
    assert windows.legal_warranty_until == date(2026, 5, 18)
    assert deadlines(store.orders[8]) is None  # not delivered yet


def test_late_shipment(store):
    assert is_late(store.orders[8], date(2026, 3, 23))
    assert not is_late(store.orders[8], date(2026, 2, 27))
