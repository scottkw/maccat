"""Golden-output parity suite (TEST-01, TEST-02).

Parametrized over all 17 *.golden.txt files in tests/golden/.

Each case patches the Python collector's module-level path constants to the
committed synthetic fake_home / Applications fixture trees, runs the
collector, normalizes the output with normalize_catalog_body(), and asserts
byte-equality against the committed .golden.txt file.

Purpose: prove the Python implementation is byte-identical to the zsh
reference for every catalog section after volatile-field normalization.
A failure names the exact section immediately in the pytest output
(e.g. test_section_parity[claude-code-plugins]).

CR-02 — the committed goldens for the 13 zsh-capturable sections are now
AUTHORITATIVELY sourced from zsh (tests/golden/generate.py::regenerate_zsh_goldens
captures real zsh output). So test_section_parity below already compares Python
against a zsh-sourced golden — it is no longer Python==Python. In ADDITION,
test_live_zsh_parity captures zsh LIVE on every macOS CI run and asserts the
Python collector reproduces the zsh body byte-for-byte. A Python regression
therefore fails the gate; it can no longer be silently absorbed by
--update-golden (which only writes the Python-format, non-zsh-capturable goldens).

Security: all patches use fixed Path objects from FAKE_HOME / FAKE_APPS.
The real HOME is never read during parity tests — all path constants are
patched before any collector.collect() call.

Note — webapps format-only caveat:
  web-installed-applications: zsh hardcodes /Applications (not overridable via
  env var). This test verifies Python format correctness only. It is one of the
  4 NON_ZSH_CAPTURABLE sections (see generate.py) whose golden is a Python-format
  golden, NOT zsh-captured — no zsh parity is claimed for it.
"""
from __future__ import annotations

import contextlib
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from maccat.catalog.format import flush_section
from maccat.collectors.chrome import ChromeCollector
from maccat.collectors.claude import ClaudeCollector
from maccat.collectors.codex import CodexCollector
from maccat.collectors.cursor import CursorCollector
from maccat.collectors.firefox import FirefoxCollector
from maccat.collectors.gemini import GeminiCollector
from maccat.collectors.homebrew import HomebrewCollector
from maccat.collectors.mas import MasCollector
from maccat.collectors.opencode import OpenCodeCollector
from maccat.collectors.setapp import SetappCollector
from maccat.collectors.vscode import VSCodeCollector
from maccat.collectors.webapps import WebAppsCollector
from tests.golden.normalize import normalize_catalog_body

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

GOLDEN_DIR = Path(__file__).parent / "golden"
FAKE_HOME = GOLDEN_DIR / "fixtures" / "fake_home"
# WR-02: the fixture dir is named "Applications" (not "fake_applications") so that
# WebAppsCollector's start-path entry (BASE.name) emits "Applications" — exactly what
# real zsh emits for its hardcoded /Applications start path. The previous name baked
# the fixture artifact "fake_applications" into the golden, a string real zsh could
# never produce, so the start-path entry carried no parity meaning.
FAKE_APPS = GOLDEN_DIR / "fixtures" / "Applications"

# WR-04: drive parametrization from the KNOWN canonical section list, NOT from a
# glob of present *.golden.txt files. A glob can only ever yield goldens that
# exist at collection time, so the "missing golden = hard fail" branch below
# could never trigger — a deleted golden would silently vanish from the suite.
# Deriving the stems from the expected 17 sections means a missing golden for an
# expected section produces a parametrized case that hits pytest.fail.
#
# Order mirrors get_registry() section order (maccat/collectors/__init__.py),
# which mirrors generate_catalog (update-list.sh:2220-2313). One stem per emitted
# section (Claude → 3, OpenCode → 3, Gemini → 2).
EXPECTED_STEMS: list[str] = [
    "homebrew-packages",
    "app-store-applications",
    "setapp-applications",
    "web-installed-applications",
    "claude-code-plugins",
    "claude-code-mcp-servers",
    "claude-code-skills-agents",
    "codex-mcp-servers",
    "opencode-plugins",
    "opencode-mcp-servers",
    "opencode-agents",
    "gemini-extensions",
    "gemini-mcp-servers",
    "vscode-extensions",
    "cursor-extensions",
    "google-chrome-extensions",
    "firefox-extensions",
]

# ---------------------------------------------------------------------------
# Parity cases invalidated by Phase 22 (ZSH-02 — versioned output)
# ---------------------------------------------------------------------------
# These three sections now emit `name (version)` lines. The frozen zsh goldens
# remain name-only (they will be deleted in Phase 23). Regenerating the goldens
# from Python output would recreate the tautological-parity anti-pattern — skip
# exactly these three cases instead and keep the remaining 14 intact.

XFAIL_STEMS: dict[str, str] = {
    "homebrew-packages": (
        "Phase 22 versioned output intentionally diverges from the frozen zsh golden "
        "(ZSH-02). Full parity suite is retired in Phase 23."
    ),
    "setapp-applications": (
        "Phase 22 versioned output intentionally diverges from the frozen zsh golden "
        "(ZSH-02). Full parity suite is retired in Phase 23."
    ),
    "web-installed-applications": (
        "Phase 22 versioned output intentionally diverges from the frozen zsh golden "
        "(ZSH-02). Full parity suite is retired in Phase 23."
    ),
}

# Webapps caveat comment (reproduced verbatim so the committed golden matches).
# web-installed-applications: zsh hardcodes /Applications — Python synthetic only.
# Zsh parity is [ASSUMED] per 17-RESEARCH.md §Assumptions A1.
_WEBAPPS_COMMENT = (
    "# web-installed-applications: zsh hardcodes /Applications"
    " -- synthetic Python fixture only\n"
    "# zsh parity for this section is [ASSUMED]"
    " per 17-RESEARCH.md §Assumptions A1\n"
)


# ---------------------------------------------------------------------------
# Per-section body builder
# ---------------------------------------------------------------------------


def _joined(items: list[str]) -> str:
    """Join items with newlines and add a trailing newline."""
    return "\n".join(items) + "\n"


def _flushed(items: list[str]) -> str:
    """flush_section (sort + dedup) then join with trailing newline."""
    return _joined(flush_section(items))


def build_section_body(section_stem: str) -> str:  # noqa: PLR0911,PLR0912
    """Dispatch to the correct collector with patched constants.

    Returns the section body text (not yet normalized).

    Patch strategy mirrors generate.py: all path constants are patched to
    FAKE_HOME subtrees before collector.collect() is called.  The real HOME
    is never accessed.

    For raw=True sections (homebrew, app-store, setapp, web-installed):
        items are joined directly — no flush_section().
    For raw=False sections:
        flush_section(items) is applied before joining.

    Claude yields 3 sections; OpenCode yields 3; Gemini yields 2.
    Each stem dispatches to the correct sub-section from the multi-section result.
    """
    if section_stem == "homebrew-packages":
        # Homebrew not installed on test runner (golden = "not installed" fallback).
        # Patch shutil.which to return None so HomebrewCollector.available() is False.
        with patch("maccat.collectors.homebrew.shutil.which", return_value=None):
            result = HomebrewCollector().collect()
        return _joined(result.sections[0].items)

    if section_stem == "app-store-applications":
        # mas not installed on test runner (golden = "not installed" fallback).
        with patch("maccat.collectors.mas.shutil.which", return_value=None):
            result = MasCollector().collect()
        return _joined(result.sections[0].items)

    if section_stem == "setapp-applications":
        # Setapp not installed — patch BASE to a guaranteed-absent path.
        with patch.object(SetappCollector, "BASE", Path("/nonexistent/Setapp")):
            result = SetappCollector().collect()
        return _joined(result.sections[0].items)

    if section_stem == "web-installed-applications":
        # web-installed-applications: zsh hardcodes /Applications — cannot synthetic-
        # match zsh.  Patch Python's BASE to FAKE_APPS and verify format only.
        # zsh parity is [ASSUMED] per 17-RESEARCH.md §Assumptions A1.
        with patch.object(WebAppsCollector, "BASE", FAKE_APPS):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        # Prepend the same caveat comments that were written when the golden was
        # generated (generate.py webapps path) so the comparison is byte-exact.
        return _WEBAPPS_COMMENT + _joined(items)

    if section_stem in {
        "claude-code-plugins",
        "claude-code-mcp-servers",
        "claude-code-skills-agents",
    }:
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch(
                    "maccat.collectors.claude._PLUGINS_PATH",
                    FAKE_HOME / ".claude/plugins/installed_plugins.json",
                )
            )
            stack.enter_context(
                patch(
                    "maccat.collectors.claude._CLAUDE_JSON",
                    FAKE_HOME / ".claude.json",
                )
            )
            stack.enter_context(
                patch(
                    "maccat.collectors.claude._SKILLS_DIR",
                    FAKE_HOME / ".claude/skills",
                )
            )
            stack.enter_context(
                patch(
                    "maccat.collectors.claude._AGENTS_DIR",
                    FAKE_HOME / ".claude/agents",
                )
            )
            result = ClaudeCollector().collect()
        _section_map = {
            "claude-code-plugins": result.sections[0],
            "claude-code-mcp-servers": result.sections[1],
            "claude-code-skills-agents": result.sections[2],
        }
        sec = _section_map[section_stem]
        return _flushed(sec.items)

    if section_stem == "codex-mcp-servers":
        with patch(
            "maccat.collectors.codex._TOML_PATH",
            FAKE_HOME / ".codex/config.toml",
        ):
            result = CodexCollector().collect()
        return _flushed(result.sections[0].items)

    if section_stem in {
        "opencode-plugins",
        "opencode-mcp-servers",
        "opencode-agents",
    }:
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch(
                    "maccat.collectors.opencode._CONFIG_PATH",
                    FAKE_HOME / ".config/opencode/opencode.json",
                )
            )
            stack.enter_context(
                patch(
                    "maccat.collectors.opencode._AGENTS_DIR",
                    FAKE_HOME / ".config/opencode/agents",
                )
            )
            result = OpenCodeCollector().collect()
        _oc_map = {
            "opencode-plugins": result.sections[0],
            "opencode-mcp-servers": result.sections[1],
            "opencode-agents": result.sections[2],
        }
        sec = _oc_map[section_stem]
        return _flushed(sec.items)

    if section_stem in {"gemini-extensions", "gemini-mcp-servers"}:
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch(
                    "maccat.collectors.gemini._EXT_DIR",
                    FAKE_HOME / ".gemini/extensions",
                )
            )
            stack.enter_context(
                patch(
                    "maccat.collectors.gemini._MCP_PATH",
                    FAKE_HOME / ".gemini/config/mcp_config.json",
                )
            )
            result = GeminiCollector().collect()
        _gem_map = {
            "gemini-extensions": result.sections[0],
            "gemini-mcp-servers": result.sections[1],
        }
        sec = _gem_map[section_stem]
        return _flushed(sec.items)

    if section_stem == "vscode-extensions":
        with patch.object(VSCodeCollector, "_EXT_DIR", FAKE_HOME / ".vscode/extensions"):
            result = VSCodeCollector().collect()
        return _flushed(result.sections[0].items)

    if section_stem == "cursor-extensions":
        with patch.object(CursorCollector, "_EXT_DIR", FAKE_HOME / ".cursor/extensions"):
            result = CursorCollector().collect()
        return _flushed(result.sections[0].items)

    if section_stem == "google-chrome-extensions":
        with patch(
            "maccat.collectors.chrome._BASE",
            FAKE_HOME / "Library/Application Support/Google/Chrome",
        ):
            result = ChromeCollector().collect()
        return _flushed(result.sections[0].items)

    if section_stem == "firefox-extensions":
        with patch(
            "maccat.collectors.firefox._FF_DIR",
            FAKE_HOME / "Library/Application Support/Firefox",
        ):
            result = FirefoxCollector().collect()
        return _flushed(result.sections[0].items)

    # Unreachable if GOLDEN_FILES covers exactly the 17 known sections.
    raise ValueError(f"Unknown section stem: {section_stem!r}")  # pragma: no cover


# ---------------------------------------------------------------------------
# Parametrized parity test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "section_stem",
    EXPECTED_STEMS,
    ids=EXPECTED_STEMS,
)
def test_section_parity(
    section_stem: str,
    update_golden: bool,
) -> None:
    """Assert Python collector output matches committed golden after normalization.

    TEST-01: Python section bodies byte-identical to zsh reference after normalization.
    TEST-02: Only the 14-digit timestamp is normalized; ALL stable fields — item
             lines (name + version + [id]), section title, sort order, (none found) —
             are asserted exactly. CR-01: the [id] field is NO LONGER erased, so a
             collector that emitted a wrong/absent ID now fails this test.

    Missing golden → pytest.fail (hard failure, not a vacuous skip). WR-04: this is
    reachable because parametrization is driven by EXPECTED_STEMS, not a glob of
    present files.
    update_golden=True (--update-golden flag) → write normalized output and skip.
    """
    # Skip parity cases invalidated by Phase 22's versioned output (ZSH-02).
    if section_stem in XFAIL_STEMS:
        pytest.skip(XFAIL_STEMS[section_stem])

    golden_file = GOLDEN_DIR / f"{section_stem}.golden.txt"

    # Build normalized Python output for this section.
    raw_body = build_section_body(section_stem)
    normalized = normalize_catalog_body(raw_body)

    if update_golden:
        # Guard: only writes when --update-golden is explicitly passed.
        # A normal pytest run NEVER reaches this branch.
        golden_file.write_text(normalized, encoding="utf-8")
        pytest.skip(f"Golden updated: {golden_file.name}")
        return  # unreachable — pytest.skip() raises; keep for type checker

    # Hard failure if golden file is absent — missing goldens are not vacuous passes.
    # WR-04: now reachable because section_stem comes from EXPECTED_STEMS.
    if not golden_file.exists():
        pytest.fail(
            f"Missing golden file: {golden_file.name}\n"
            f"Run `pytest --update-golden` to generate it."
        )

    # WR-05: compare the committed golden VERBATIM. The golden is already the
    # post-normalization source of truth (written via --update-golden, which
    # stores `normalized`). Re-normalizing it at read time would silently scrub
    # an accidental raw timestamp/label baked into a bad golden on BOTH sides,
    # hiding the regression. Only the freshly-produced Python output is normalized.
    expected = golden_file.read_text(encoding="utf-8")
    assert normalized == expected, (
        f"Section '{section_stem}' parity failed.\n"
        f"Run with --update-golden to refresh if the format change is intentional."
    )


# ---------------------------------------------------------------------------
# Live zsh-parity test (CR-02)
# ---------------------------------------------------------------------------
#
# This is the test that gives the acceptance gate real teeth. For every
# zsh-capturable section it sources update-list.sh in REAL zsh against the
# fixture, extracts the section body, and asserts the Python collector output
# equals the live zsh output (both normalized). Because zsh is captured fresh on
# every run, a Python regression (e.g. a wrong/absent [id]) FAILS here — there is
# no committed intermediary that --update-golden could overwrite.
#
# Guarded so non-macOS dev machines without zsh skip cleanly; on macos-latest CI
# (zsh always present) it MUST run.

_ZSH_AVAILABLE = shutil.which("zsh") is not None

# Lazily resolved inside the test body to avoid importing generate.py (which
# drives zsh subprocesses) at collection time. The parametrize IDs come from the
# canonical ZSH_CAPTURABLE keys.
from tests.golden.generate import ZSH_CAPTURABLE  # noqa: E402

_ZSH_CAPTURABLE_STEMS: list[str] = list(ZSH_CAPTURABLE.keys())


@pytest.mark.zsh_parity
@pytest.mark.skipif(
    not _ZSH_AVAILABLE,
    reason="zsh not on PATH (non-macOS dev machine); runs in macos-latest CI.",
)
@pytest.mark.parametrize(
    "section_stem",
    _ZSH_CAPTURABLE_STEMS,
    ids=_ZSH_CAPTURABLE_STEMS,
)
def test_live_zsh_parity(section_stem: str) -> None:
    """Assert Python collector output == LIVE zsh output for a zsh-capturable section.

    CR-02: locks Python <-> zsh equivalence on every macOS CI run. The zsh body
    is captured fresh from update-list.sh (byte-unmodified reference, TEST-04),
    not from any committed golden, so a Python regression cannot be masked.
    Both sides are normalized identically (only the 14-digit timestamp is
    volatile; the [id] field is preserved and asserted).
    """
    from tests.golden.generate import FAKE_HOME as ZSH_FAKE_HOME
    from tests.golden.generate import capture_zsh_section_body

    collector_fn = ZSH_CAPTURABLE[section_stem]
    zsh_body = capture_zsh_section_body(collector_fn, ZSH_FAKE_HOME)
    zsh_normalized = normalize_catalog_body(zsh_body)

    python_normalized = normalize_catalog_body(build_section_body(section_stem))

    assert python_normalized == zsh_normalized, (
        f"LIVE zsh parity FAILED for section '{section_stem}'.\n"
        f"Python collector output diverged from update-list.sh ({collector_fn}).\n"
        f"--- python ---\n{python_normalized!r}\n--- zsh ---\n{zsh_normalized!r}"
    )
