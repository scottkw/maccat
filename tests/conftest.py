from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_json(tmp_path: Path):
    """Factory fixture: write a dict as JSON to a temp file, return the Path."""

    def _write(data: dict, filename: str = "test.json") -> Path:
        p = tmp_path / filename
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    return _write


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Disposable git repo (no remote) for catalog operations.

    All retention/identity/config tests MUST use this fixture — never the real
    personal/office directories. Isolation is guaranteed by pytest's tmp_path.
    """
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        capture_output=True,
    )
    return tmp_path


@pytest.fixture()
def catalog_repo(git_repo: Path) -> Path:
    """Git repo pre-populated with a personal/ computer folder containing one catalog file.

    Builds on git_repo (disposable, isolated). Returns the repo root Path.
    """
    from maccat.naming import make_catalog_filename

    computer_dir = git_repo / "personal"
    computer_dir.mkdir()
    catalog = computer_dir / make_catalog_filename("personal", "20260614120000")
    catalog.write_text("test catalog", encoding="utf-8")
    return git_repo


# ---------------------------------------------------------------------------
# --update-golden flag (TEST-01/02 golden fixture update guard)
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help=(
            "Regenerate golden fixture files from current Python collector output. "
            "Only run manually when a format change is intentional. "
            "NEVER triggers on a normal `pytest` run."
        ),
    )


@pytest.fixture()
def update_golden(request: pytest.FixtureRequest) -> bool:
    """True only when --update-golden is passed on the command line."""
    return request.config.getoption("--update-golden")  # type: ignore[no-any-return]
