"""Opening hours (manual §2) with national and Mato Grosso do Sul holidays.

Municipal dates in Campo Grande (Corpus Christi, Santo Antônio on 13/06, the city anniversary
on 26/08) are treated as working days: commerce usually opens on them. To confirm with the store.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from emporio.clock import STORE_TZ, WEEKDAYS, fmt_date, fmt_moment

# date.weekday() -> (opens, closes). Sunday (6) is closed.
OPENING_HOURS: dict[int, tuple[time, time]] = {
    **{weekday: (time(9), time(18)) for weekday in range(5)},
    5: (time(9), time(13)),
}

_FIXED_HOLIDAYS = {
    (1, 1): "Confraternização Universal",
    (4, 21): "Tiradentes",
    (5, 1): "Dia do Trabalho",
    (9, 7): "Independência do Brasil",
    (10, 11): "Criação do Estado de Mato Grosso do Sul",
    (10, 12): "Nossa Senhora Aparecida",
    (11, 2): "Finados",
    (11, 15): "Proclamação da República",
    (11, 20): "Dia Nacional de Zumbi e da Consciência Negra",
    (12, 25): "Natal",
}


def easter(year: int) -> date:
    """Gregorian Easter Sunday (Meeus/Jones/Butcher)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    w = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * w) // 451
    month, day = divmod(h + w - 7 * m + 114, 31)
    return date(year, month, day + 1)


def holidays(year: int) -> dict[date, str]:
    days = {date(year, month, day): name for (month, day), name in _FIXED_HOLIDAYS.items()}
    days[easter(year) - timedelta(days=2)] = "Sexta-feira da Paixão"
    return days


def holiday_name(day: date) -> str | None:
    return holidays(day.year).get(day)


def opening_window(day: date) -> tuple[datetime, datetime] | None:
    if holiday_name(day) or day.weekday() not in OPENING_HOURS:
        return None
    opens, closes = OPENING_HOURS[day.weekday()]
    return datetime.combine(day, opens, STORE_TZ), datetime.combine(day, closes, STORE_TZ)


@dataclass(frozen=True)
class StoreStatus:
    at: datetime
    is_open: bool
    closes_at: datetime | None = None
    next_opening: datetime | None = None
    closed_reason: str | None = None


def store_status(at: datetime) -> StoreStatus:
    at = at.astimezone(STORE_TZ)
    today = opening_window(at.date())
    if today and today[0] <= at < today[1]:
        return StoreStatus(at, True, closes_at=today[1])
    for offset in range(15):
        window = opening_window(at.date() + timedelta(days=offset))
        if window and window[0] > at:
            return StoreStatus(at, False, next_opening=window[0], closed_reason=_closed_reason(at))
    raise RuntimeError("no opening found in the next two weeks")


def _closed_reason(at: datetime) -> str:
    name = holiday_name(at.date())
    if name:
        return f"feriado: {name}"
    if at.weekday() not in OPENING_HOURS:
        return "domingo"
    if at.time() < OPENING_HOURS[at.weekday()][0]:
        return "antes do horário de abertura"
    return "depois do horário de atendimento"


def describe(status: StoreStatus) -> str:
    """One line for the system prompt."""
    head = f"Agora em Campo Grande: {fmt_moment(status.at)}."
    if status.is_open:
        return f"{head} A loja está aberta e fecha hoje às {status.closes_at:%H:%M}."
    reopen = status.next_opening
    article = "no" if reopen.weekday() >= 5 else "na"  # no sábado, na segunda-feira
    text = (
        f"{head} A loja está fechada ({status.closed_reason}). A equipe volta {article} "
        f"{WEEKDAYS[reopen.weekday()]}, {fmt_date(reopen)}, às {reopen:%H:%M}."
    )
    skipped = []  # holidays between today and the reopening, so the customer knows why it takes longer
    for offset in range(1, (reopen.date() - status.at.date()).days):
        day = status.at.date() + timedelta(days=offset)
        name = holiday_name(day)
        if name:
            skipped.append(f"{WEEKDAYS[day.weekday()]}, {fmt_date(day)} ({name})")
    if skipped:
        text += f" Antes disso não abre por feriado: {'; '.join(skipped)}."
    return text
