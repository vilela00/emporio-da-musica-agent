"""Store clock: Campo Grande local time (UTC-4, one hour behind Brasília)."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
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


# Set per request by the browser demo, which lets the widget pick the store clock. A context variable,
# not the environment, so two requests never see each other's clock; LangGraph and LangChain copy the
# context into the threads where nodes and tools run.
_frozen: ContextVar[datetime | None] = ContextVar("store_clock", default=None)


def now() -> datetime:
    """Current store time. frozen_at() or EMPORIO_NOW (ISO 8601, store local time) replace the real clock."""
    moment = _frozen.get()
    if moment is None:
        frozen = os.getenv("EMPORIO_NOW")
        if not frozen:
            return datetime.now(STORE_TZ)
        moment = datetime.fromisoformat(frozen)
    return moment if moment.tzinfo else moment.replace(tzinfo=STORE_TZ)


@contextmanager
def frozen_at(moment: datetime | None) -> Iterator[None]:
    """Store clock fixed at moment inside the block; None means no override (EMPORIO_NOW or the real clock)."""
    token = _frozen.set(moment)
    try:
        yield
    finally:
        _frozen.reset(token)


def fmt_date(day: date) -> str:
    return day.strftime("%d/%m/%Y")


def fmt_moment(moment: datetime) -> str:
    return f"{WEEKDAYS[moment.weekday()]}, {fmt_date(moment)}, {moment:%H:%M}"
