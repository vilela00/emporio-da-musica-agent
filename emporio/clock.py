"""Store clock: Campo Grande local time (UTC-4, one hour behind Brasília)."""

from __future__ import annotations

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

STORE_TZ = ZoneInfo("America/Campo_Grande")

WEEKDAYS = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)


def now() -> datetime:
    """Current store time. EMPORIO_NOW (ISO 8601, store local time) freezes it for tests and demos."""
    frozen = os.getenv("EMPORIO_NOW")
    if frozen:
        moment = datetime.fromisoformat(frozen)
        return moment if moment.tzinfo else moment.replace(tzinfo=STORE_TZ)
    return datetime.now(STORE_TZ)


def fmt_date(day: date) -> str:
    return day.strftime("%d/%m/%Y")


def fmt_moment(moment: datetime) -> str:
    return f"{WEEKDAYS[moment.weekday()]}, {fmt_date(moment)}, {moment:%H:%M}"
