"""Nothing hidden in the repository: .env stays out of git, no file carries an API key, and no source
file carries invisible characters (a bidi control in code can make it read differently than it runs)."""

import os
import re
from pathlib import Path

from emporio.safety import invisible

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


def written_by_hand(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        path.suffix in {".py", ".toml", ".txt", ".example"}
        or relative.name == "README.md"
        or relative.parts[0] == "docs"
    )


def test_no_invisible_characters_in_what_people_wrote():
    hidden = [
        str(path.relative_to(ROOT))
        for path in repository_files()
        if written_by_hand(path) and any(map(invisible, path.read_text(encoding="utf-8")))
    ]
    assert hidden == []
