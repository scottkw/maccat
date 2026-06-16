"""Zsh golden-capture harness — the AUTHORITATIVE source for zsh-capturable goldens.

CR-02: This module is what makes the parity gate genuinely verify Python==zsh
rather than Python==Python. The committed ``*.golden.txt`` for every
zsh-capturable (HOME-driven, file-based) section is produced HERE, by sourcing
update-list.sh in real zsh against the synthetic fake_home fixture and capturing
the collector's section BODY. The Python parity suite then asserts the Python
collector output equals those zsh-sourced goldens. A Python regression therefore
fails the gate (it can no longer be silently absorbed by ``--update-golden``,
which previously wrote Python output back over the goldens).

Run ``python tests/golden/generate.py`` (or ``python -m tests.golden.generate``)
to regenerate the zsh-capturable goldens FROM ZSH. The 4 non-zsh-capturable
sections (homebrew/mas — CLI-driven; setapp/webapps — hardcoded /Applications,
not overridable via HOME) are NOT touched here; their goldens remain
Python-format goldens (see ZSH_CAPTURABLE / NON_ZSH_CAPTURABLE below and the
honest caveat in test_golden_parity.py).

NEVER import this module on a normal pytest run — it drives real zsh subprocesses
against synthetic HOME trees. Importing it at test collection time (e.g. at module
level in a test file) would trigger zsh on every pytest run. The live zsh-parity
test in test_golden_parity.py imports ``capture_zsh_section_body`` lazily, inside
the test body, guarded by a zsh-availability skip.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.parent
SCRIPT = REPO_ROOT / "update-list.sh"
GOLDEN_DIR = Path(__file__).parent
FAKE_HOME = GOLDEN_DIR / "fixtures" / "fake_home"

# IN-03: manual-only / CI harness; generous margin so a cold macOS runner
# sourcing the full ~2500-line script does not flake on the first zsh launch.
_ZSH_TIMEOUT_SECONDS = 30

# Section body header written by write_section (update-list.sh:1075):
#   echo "\n{title}"; echo "------------------------------------"
# i.e. OUTPUT_FILE gets "\n{title}\n" + 36 dashes + "\n" before the body.
SEPARATOR_LINE = "-" * 36


# ---------------------------------------------------------------------------
# Section -> zsh collector mapping (CR-02)
# ---------------------------------------------------------------------------
#
# ZSH_CAPTURABLE: sections whose zsh collector resolves every input path from
# $HOME and can therefore be driven against the synthetic fake_home fixture.
# These goldens are AUTHORITATIVELY sourced from zsh (this module) and the live
# zsh-parity test locks Python == zsh for each on every macOS CI run.
#
# golden stem -> zsh collector function name (update-list.sh).
ZSH_CAPTURABLE: dict[str, str] = {
    "claude-code-plugins": "collect_claude_plugins",
    "claude-code-mcp-servers": "collect_claude_mcp",
    "claude-code-skills-agents": "collect_claude_skills_agents",
    "codex-mcp-servers": "collect_codex_mcp",
    "opencode-plugins": "collect_opencode_plugins",
    "opencode-mcp-servers": "collect_opencode_mcp",
    "opencode-agents": "collect_opencode_agents",
    "gemini-extensions": "collect_gemini_extensions",
    "gemini-mcp-servers": "collect_gemini_mcp",
    "vscode-extensions": "collect_vscode_extensions",
    "cursor-extensions": "collect_cursor_extensions",
    "google-chrome-extensions": "collect_chrome_extensions",
    "firefox-extensions": "collect_firefox_extensions",
}

# NON_ZSH_CAPTURABLE: sections whose zsh collector CANNOT be driven against the
# fixture, so their goldens are Python-format goldens — NOT zsh-captured. We do
# NOT claim zsh parity for these (no silent overclaim):
#   - homebrew-packages / app-store-applications: driven by external CLIs
#     (brew/mas) whose installed state cannot be faked via HOME.
#   - setapp-applications / web-installed-applications: zsh hardcodes
#     /Applications (and /Applications/Setapp), not overridable via HOME, so the
#     fixture cannot be substituted in the zsh process.
NON_ZSH_CAPTURABLE: frozenset[str] = frozenset(
    {
        "homebrew-packages",
        "app-store-applications",
        "setapp-applications",
        "web-installed-applications",
    }
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def capture_zsh_section(
    collector_fn: str,
    fake_home: Path,
) -> str:
    """Source update-list.sh in zsh, call one collector, return OUTPUT_FILE text.

    Returns the FULL section text as written to OUTPUT_FILE:
    ``\\n{title}\\n{separator}\\n{body}``. Use capture_zsh_section_body() to get
    just the body (what the parity suite compares against the committed goldens).

    Verified: source-guard at update-list.sh:2433 fires before main block.

    Required globals set in the zsh script body (NOT via env=):
      OUTPUT_FILE — collectors append section text here (NOT stdout)
      HOME        — override to fake_home before any ~/.* path resolution
      _section_lines=() — reset before each call (collector contract per line 1237-1241)

    WR-06: SCRIPT_DIR is deliberately NOT set here. update-list.sh:42
    unconditionally reassigns ``SCRIPT_DIR="${0:A:h}"`` while sourcing, so any
    harness-supplied value would be overwritten and is therefore dead. No collector
    reads SCRIPT_DIR, so the override is harmless for this capture path.

    Security: all path interpolations use !r (repr) producing quoted shell strings
    that prevent word-splitting and glob expansion. All paths come from Python
    Path objects constructed from repo structure — no untrusted input.

    One-collector-per-call rule: always call with exactly ONE collector_fn.
    Each invocation gets a fresh zsh process. Never call two collectors in one
    -c script body — _section_lines is global in zsh and leaks between calls
    (RESEARCH.md Pitfall 3).

    Read OUTPUT_FILE (temp file), never result.stdout — stdout carries progress
    messages from echo calls, not section text (RESEARCH.md Pitfall 2).
    """
    with tempfile.NamedTemporaryFile(mode="r", suffix=".txt", delete=False) as f:
        output_file = Path(f.name)
    try:
        zsh_script = f"""
OUTPUT_FILE={str(output_file)!r}
HOME={str(fake_home)!r}
_section_lines=()
source {str(SCRIPT)!r}
{collector_fn}
"""
        result = subprocess.run(
            ["zsh", "-c", zsh_script],
            capture_output=True,
            text=True,
            timeout=_ZSH_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"zsh collector {collector_fn!r} failed "
                f"(rc={result.returncode}):\n{result.stderr}"
            )
        return output_file.read_text(encoding="utf-8")
    finally:
        output_file.unlink(missing_ok=True)


def capture_zsh_section_body(collector_fn: str, fake_home: Path) -> str:
    """Capture a zsh section and return ONLY its body (item lines).

    Strips the leading ``\\n{title}\\n{separator}\\n`` header written by
    write_section so the result is byte-comparable with the committed
    body-goldens AND with the Python collector output (which the parity suite
    builds as body only). The split is on ``\\n{SEPARATOR_LINE}\\n`` — the exact
    delimiter write_section emits — with maxsplit=1 so only the FIRST separator
    (the section header's) is consumed; a body that itself contained a 36-dash
    line would not be mis-split.
    """
    full = capture_zsh_section(collector_fn, fake_home)
    delimiter = "\n" + SEPARATOR_LINE + "\n"
    parts = full.split(delimiter, 1)
    if len(parts) != 2:
        raise RuntimeError(
            f"zsh collector {collector_fn!r} output missing the "
            f"write_section separator; cannot extract body:\n{full!r}"
        )
    return parts[1]


def regenerate_zsh_goldens() -> list[str]:
    """Regenerate every ZSH_CAPTURABLE golden FROM ZSH and write it to GOLDEN_DIR.

    This is the authoritative regeneration path for the zsh-capturable sections
    (CR-02). It does NOT touch the NON_ZSH_CAPTURABLE Python-format goldens.

    Because update-list.sh is the byte-unmodified reference (TEST-04), capturing
    here and committing the result means the committed goldens ARE the zsh output;
    the parity suite then proves the Python collector reproduces them.

    Returns the list of golden stems written.
    """
    if shutil.which("zsh") is None:
        raise RuntimeError("zsh not on PATH — cannot regenerate zsh-sourced goldens.")

    written: list[str] = []
    for stem, collector_fn in ZSH_CAPTURABLE.items():
        body = capture_zsh_section_body(collector_fn, FAKE_HOME)
        golden_path = GOLDEN_DIR / f"{stem}.golden.txt"
        golden_path.write_text(body, encoding="utf-8")
        written.append(stem)
    return written


def main() -> None:
    """CLI entrypoint: regenerate zsh-capturable goldens from zsh."""
    written = regenerate_zsh_goldens()
    print(f"Regenerated {len(written)} zsh-sourced goldens:")
    for stem in written:
        print(f"  {stem}.golden.txt")
    print(
        "\nNOTE: the 4 non-zsh-capturable sections "
        "(homebrew/mas/setapp/webapps) are NOT regenerated here; "
        "they are Python-format goldens (see NON_ZSH_CAPTURABLE)."
    )


if __name__ == "__main__":
    main()
