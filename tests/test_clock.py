from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from datetime import datetime

from emporio import clock


def test_frozen_at_wins_over_the_environment_and_is_undone(monkeypatch):
    monkeypatch.setenv("EMPORIO_NOW", "2026-04-03T19:40")
    with clock.frozen_at(datetime(2026, 3, 23, 10, 30)):
        assert clock.now() == datetime(2026, 3, 23, 10, 30, tzinfo=clock.STORE_TZ)
        with clock.frozen_at(None):
            assert clock.now().day == 3  # None falls back to EMPORIO_NOW
    assert clock.now() == datetime(2026, 4, 3, 19, 40, tzinfo=clock.STORE_TZ)


def test_frozen_clock_reaches_threads_that_copy_the_context():
    # LangGraph and LangChain run nodes and tools this way (copy_context().run in a pool)
    with clock.frozen_at(datetime(2026, 3, 23, 10, 30)), ThreadPoolExecutor(1) as pool:
        assert pool.submit(copy_context().run, clock.now).result().day == 23
