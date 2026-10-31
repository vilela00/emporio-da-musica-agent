"""Nothing secret in the repository: .env stays out of git and no file carries an API key."""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOOGLE_KEY = re.compile(r"AIza[0-9A-Za-z_\-]{35}")
NOT_COMMITTED = {".git", ".venv", "var", "__pycache__", ".pytest_cache", ".ruff_cache"}


def repository_files():
    for folder, subfolders, files in os.walk(ROOT):
        subfolders[:] = [name for name in subfolders if name not in NOT_COMMITTED]
        yield from (Path(folder) / name for name in files if name != ".env")


def test_no_api_key_in_any_file():
    leaks = [
        str(path.relative_to(ROOT))
        for path in repository_files()
        if GOOGLE_KEY.search(path.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert leaks == []


def test_env_and_runtime_state_stay_out_of_git():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignored and "var/" in ignored


def test_example_env_ships_without_a_key():
    assert "GOOGLE_API_KEY=" in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
