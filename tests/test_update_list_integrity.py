"""TEST-04: update-list.sh integrity check.

Verifies update-list.sh passes zsh -n (syntax check) at all times.
Acts as a tripwire — if update-list.sh is accidentally modified during Python
development, CI fails here before any parity tests run.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def test_update_list_passes_zsh_syntax_check() -> None:
    """TEST-04: update-list.sh must pass zsh -n at milestone end."""
    result = subprocess.run(
        ["zsh", "-n", str(REPO_ROOT / "update-list.sh")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"update-list.sh failed zsh -n:\n{result.stderr}"
