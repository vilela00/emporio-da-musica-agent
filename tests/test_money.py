from decimal import Decimal

from emporio.money import brl, money_mentions


def test_brl_format():
    assert brl(Decimal("2199")) == "R$ 2.199,00"
    assert brl("1967.175") == "R$ 1.967,18"
    assert brl(35) == "R$ 35,00"


def test_money_mentions_reads_brazilian_amounts():
    text = "De R$ 2.399,00 por R$1.967,18, ou 12x de 183,25. Orçamento até R$1000 e frete R$ 35."
    assert money_mentions(text) == {
        Decimal("2399.00"), Decimal("1967.18"), Decimal("183.25"), Decimal("1000.00"), Decimal("35.00"),
    }


def test_money_mentions_ignores_dates_phones_and_codes():
    text = "Pedido #7 de 03/02/2026, rastreio BRKR1122334BR, ligue (67) 3341-4444, 18% off, 650mm."
    assert money_mentions(text) == set()
