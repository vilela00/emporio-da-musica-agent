from datetime import datetime

from emporio.agent.prompts import Session, customer_line, system_prompt
from emporio.clock import STORE_TZ


def test_known_customer_is_named_by_first_name(store):
    assert "Letícia (Campo Grande)" in customer_line(store, Session(phone="+55 67 99789-0123"))
    assert "não está no cadastro" in customer_line(store, Session(phone="+55 67 90000-0000"))
    assert "não identificado" in customer_line(store, Session())


def test_prompt_carries_clock_and_guard_note(store):
    at = datetime(2026, 4, 3, 19, 40, tzinfo=STORE_TZ)
    text = system_prompt(store, Session(), at, guard_note="ATENÇÃO: teste")
    assert "Sexta-feira da Paixão" in text and "sábado, 04/04/2026, às 09:00" in text
    assert text.rstrip().endswith("ATENÇÃO: teste")
