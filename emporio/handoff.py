"""Tickets for the human team (manual §7.3 complaints, §10 'ask the manager when in doubt')."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

REASONS = {
    "reclamacao": "Reclamação",
    "troca_ou_devolucao": "Troca ou devolução",
    "garantia": "Garantia",
    "pedido_especial": "Pedido especial ou item fora do sistema",
    "duvida_de_politica": "Dúvida sobre política (consultar a gerência)",
    "dados_pessoais": "Dados pessoais (LGPD)",
    "outro": "Outro",
}


@dataclass(frozen=True)
class Ticket:
    protocol: str
    created_at: str
    reason: str
    summary: str
    phone: str | None
    customer: str | None
    orders: str | None = None  # filled by the system, not by the model


def open_ticket(
    var_dir: Path,
    *,
    at: datetime,
    reason: str,
    summary: str,
    phone: str | None,
    customer: str | None,
    orders: str | None = None,
) -> Ticket:
    var_dir.mkdir(parents=True, exist_ok=True)
    path = var_dir / "handoffs.jsonl"
    prefix = f"EM-{at:%Y%m%d}-"
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    sequence = 1 + sum(json.loads(line)["protocol"].startswith(prefix) for line in existing if line)
    ticket = Ticket(
        protocol=f"{prefix}{sequence:03d}",
        created_at=at.isoformat(timespec="minutes"),
        reason=reason if reason in REASONS else "outro",
        summary=summary.strip(),
        phone=phone,
        customer=customer,
        orders=orders,
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(ticket), ensure_ascii=False) + "\n")
    return ticket
