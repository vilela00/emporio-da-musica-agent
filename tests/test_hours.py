from datetime import UTC, date, datetime

from emporio.clock import STORE_TZ
from emporio.hours import describe, easter, holidays, store_status


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=STORE_TZ)


def test_easter_and_good_friday():
    assert easter(2026) == date(2026, 4, 5)
    assert easter(2027) == date(2027, 3, 28)
    assert holidays(2026)[date(2026, 4, 3)] == "Sexta-feira da Paixão"


def test_state_and_black_consciousness_holidays():
    days = holidays(2026)
    assert date(2026, 10, 11) in days  # Criação do Estado de MS
    assert date(2026, 11, 20) in days  # national since 2024


def test_open_on_a_weekday_morning():
    status = store_status(at("2026-03-23T10:30"))
    assert status.is_open and status.closes_at.hour == 18


def test_good_friday_evening_reopens_saturday_morning():
    status = store_status(at("2026-04-03T19:40"))
    assert not status.is_open
    assert status.closed_reason == "feriado: Sexta-feira da Paixão"
    assert status.next_opening == at("2026-04-04T09:00")


def test_saturday_afternoon_skips_sunday_and_finados():
    status = store_status(at("2026-10-31T15:00"))
    assert not status.is_open
    assert status.next_opening == at("2026-11-03T09:00")
    assert "terça-feira, 03/11/2026, às 09:00" in describe(status)
    assert "segunda-feira, 02/11/2026 (Finados)" in describe(status)


def test_saturday_closes_at_one():
    assert store_status(at("2026-10-31T12:59")).is_open
    assert not store_status(at("2026-10-31T13:00")).is_open


def test_campo_grande_is_one_hour_behind_brasilia():
    # 13:00 UTC is 10:00 in Brasília but 09:00 in Campo Grande: the store has just opened.
    status = store_status(datetime(2026, 3, 23, 13, 0, tzinfo=UTC))
    assert status.is_open and status.at.hour == 9
