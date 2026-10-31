import json
from datetime import datetime

from emporio.clock import STORE_TZ
from emporio.handoff import open_ticket


def test_protocol_sequence_per_day(tmp_path):
    at = datetime(2026, 4, 3, 19, 40, tzinfo=STORE_TZ)
    first = open_ticket(tmp_path, at=at, reason="reclamacao", summary=" atraso ", phone="67", customer="Ana")
    second = open_ticket(tmp_path, at=at, reason="xyz", summary="outro", phone=None, customer=None)
    assert first.protocol == "EM-20260403-001" and second.protocol == "EM-20260403-002"
    assert second.reason == "outro"
    lines = (tmp_path / "handoffs.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["summary"] == "atraso"
