"""Run the scenarios against the real model and write evals/report.md.

    uv run python -m evals.run                 # all scenarios
    uv run python -m evals.run --only S04,S16  # a subset
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from emporio.agent import DEFAULT_MODEL
from emporio.agent.guard import ungrounded
from emporio.safety import redact
from evals.scenarios import SCENARIOS, Scenario

REPORT = Path(__file__).parent / "report.md"


def check(s: Scenario, replies: list[str], called: list[str]) -> list[str]:
    text = "\n".join(replies)
    failures = [f"tool not called: {t}" for t in s.tools if not any(re.fullmatch(t, c) for c in called)]
    failures += [f"missing: /{p}/" for p in s.must if not re.search(p, text, re.IGNORECASE)]
    failures += [f"should not say: /{p}/" for p in s.must_not if re.search(p, text, re.IGNORECASE)]
    return failures


def main() -> None:
    load_dotenv()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="comma-separated scenario ids")
    parser.add_argument("--delay", type=float, default=3.0, help="seconds between scenarios (free-tier rate limits)")
    args = parser.parse_args()
    chosen = [s for s in SCENARIOS if not args.only or s.id in args.only.split(",")]

    from emporio.agent.runner import Agent

    # tickets opened by this run go to their own file, numbered from 001, not to the store's var/handoffs.jsonl
    os.environ["EMPORIO_VAR_DIR"] = str(Path("var") / "evals")
    (Path("var") / "evals" / "handoffs.jsonl").unlink(missing_ok=True)
    agent = Agent(db_path=Path("var") / "evals.sqlite")
    rows, details, quota_errors = [], [], 0
    for index, s in enumerate(chosen):
        if quota_errors >= 2:
            print(f"{s.id} skip  the provider is refusing calls (quota or billing)")
            continue
        if index:
            time.sleep(args.delay)
        os.environ["EMPORIO_NOW"] = s.now
        thread = agent.thread_for(s.phone, fresh=True)
        replies, called, models, started = [], [], [], time.perf_counter()
        outputs, said, leaks = [], [], []
        try:
            for message in s.turns:
                turn = agent.reply(thread, s.phone, message)
                replies.append(turn.text)
                called += [name for name, _ in turn.tool_calls]
                models += [m for m in turn.models if m not in models]
                outputs += turn.tool_outputs
                said.append(message)
                leaks += ungrounded(turn.text, outputs, said)  # the guard should have stopped these
            failures = check(s, replies, called) + [f"not grounded: {x}" for x in leaks]
        except Exception as error:  # a crash is a failed scenario, not a crashed run
            failures = [f"error: {type(error).__name__}: {redact(str(error))[:300]}"]
            quota_errors += "RESOURCE_EXHAUSTED" in str(error) or "402" in str(error)
        seconds = time.perf_counter() - started
        status = "pass" if not failures else "FAIL"
        print(f"{s.id} {status:4} {seconds:5.1f}s  {s.title}" + (f"  -> {'; '.join(failures)}" if failures else ""))
        rows.append(
            f"| {s.id} | {s.title} | {s.covers} | {', '.join(dict.fromkeys(called)) or '-'} "
            f"| {', '.join(models) or '-'} | {status} |"
        )
        conversation = "\n\n".join(f"**Customer:** {m}\n\n**Tom:** {r}" for m, r in zip(s.turns, replies, strict=False))
        notes = "".join(f"\n- {f}" for f in failures)
        details.append(f"### {s.id} {s.title} ({status}, {seconds:.1f}s)\n{notes}\n\n{conversation}\n")
    passed = sum(row.endswith("| pass |") for row in rows)
    model = os.getenv("LLM_MODEL", DEFAULT_MODEL)
    header = [
        "# Evaluation report",
        "",
        f"Model `{model}`, run on {datetime.now():%Y-%m-%d %H:%M}. "
        f"**{passed}/{len(rows)} scenarios passed.** Scenarios and checks: `evals/scenarios.py`.",
        "",
        "| ID | Scenario | Covers | Tools called | Model | Result |",
        "|---|---|---|---|---|---|",
    ]
    REPORT.write_text("\n".join(header + rows + ["", "## Replies", ""] + details), encoding="utf-8")
    print(f"\n{passed}/{len(rows)} passed. Report: {REPORT}")


if __name__ == "__main__":
    main()
