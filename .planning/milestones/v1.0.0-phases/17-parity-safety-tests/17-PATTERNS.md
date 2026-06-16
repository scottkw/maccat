# Phase 17: Parity & Safety Tests — Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 9 new files + 1 file modified (conftest.py)
**Analogs found:** 10 / 10

Each new file has one or two analogs:
1. A Python structural analog — the code style, fixture, and import pattern to copy.
2. A zsh behavioral analog — the functions being captured for parity (where applicable).

---

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `tests/golden/normalize.py` | utility | transform | `src/maccat/catalog/format.py` (pure function module) | role-match |
| `tests/golden/generate.py` | utility | request-response (zsh subprocess) | `tests/conftest.py` `git_repo` fixture (subprocess pattern) | role-match |
| `tests/golden/*.golden.txt` (17 files) | fixture | — | `tests/conftest.py` `catalog_repo` fixture (committed artifact) | role-match |
| `tests/test_golden_parity.py` | test | transform | `tests/collectors/test_chrome.py` (parametrize + patch.object + tmp_path) | role-match |
| `tests/test_safety_invariants.py` | test | CRUD | `tests/test_retention.py` + `tests/test_identity.py` (logic source) | exact |
| `tests/test_update_list_integrity.py` | test | request-response | `tests/test_retention.py` `TestPruneOldArchives` (subprocess via patch) | role-match |
| `.github/workflows/ci.yml` | config | — | No existing analog (no `.github/` yet) | none |
| `tests/conftest.py` (modify) | config | — | `tests/conftest.py` itself (extend existing) | exact |

---

## Pattern Assignments

---

### `tests/golden/normalize.py` (utility, transform)

**Analog:** `src/maccat/catalog/format.py` (module header convention)

**Module header pattern** (copy from `src/maccat/catalog/format.py` lines 1–5):
```python
"""Normalization helpers for golden-output parity tests (TEST-02).

Strips volatile fields before byte comparison so stable fields are asserted exactly.
"""
from __future__ import annotations

import re
```

**Core function — specified verbatim in CONTEXT.md and RESEARCH.md:**
```python
def normalize_catalog_body(text: str) -> str:
    """Strip volatile fields before byte comparison.

    Volatile (replaced):
    - 14-digit timestamps anywhere in text → TIMESTAMP
    - Square-bracket machine labels like [computer-one] → [MACHINE]

    Stable (asserted exactly after normalization):
    - Section headers, separator lines, item lines, sort order, (none found)
    """
    text = re.sub(r'\d{14}', 'TIMESTAMP', text)
    text = re.sub(r'\[[^\]]+\]', '[MACHINE]', text)
    return text
```

**Section-split helper — per RESEARCH.md Q4:**
```python
SEPARATOR_LINE = "-" * 36

def extract_section_body(catalog_text: str, section_title: str) -> str | None:
    """Return the body text for a named section, or None if not found.

    Format from CatalogWriter.write_section: \\n{title}\\n{separator}\\n{body}.
    Split on \\n + separator + \\n; the chunk before each separator ends with
    the title line; the chunk after it is the body.
    """
    parts = catalog_text.split("\n" + SEPARATOR_LINE + "\n")
    for i, part in enumerate(parts):
        if part.rstrip("\n").endswith(section_title) and i + 1 < len(parts):
            body_chunk = parts[i + 1]
            # Body ends before the next \\n\\n<title> boundary
            return body_chunk.split("\n\n")[0]
    return None
```

**Key constraints:**
- Pure functions only — no fixtures, no imports from maccat.
- No `sorted()` calls — the golden text is already C-locale-sorted by zsh's `flush_section`.
- Both functions must be importable from `tests.golden.normalize` (add `tests/golden/__init__.py` if needed, or ensure `tests/golden/` is on `sys.path` via conftest).

---

### `tests/golden/generate.py` (utility, zsh subprocess golden capture)

**Analog:** `tests/conftest.py` `git_repo` fixture (subprocess.run pattern, lines 29–40)

**Subprocess call convention** (copy `capture_output=True, check=True` style from conftest.py line 29):
```python
result = subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
```

**Core capture function — verified by live zsh test in RESEARCH.md Q1:**
```python
# tests/golden/generate.py
"""Zsh golden-capture harness.  Called ONLY when --update-golden is passed.

NEVER import this module on a normal pytest run — the generate() function
drives real zsh subprocesses against synthetic HOME trees.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
SCRIPT = REPO_ROOT / "update-list.sh"


def capture_zsh_section(
    collector_fn: str,
    fake_home: Path,
) -> str:
    """Source update-list.sh in zsh, call one collector, return OUTPUT_FILE text.

    Verified: source-guard at update-list.sh:2433 fires before main block.
    Required globals:
      OUTPUT_FILE — collectors append section text here (NOT stdout)
      HOME        — override to fake_home before any ~/.* path resolution
      SCRIPT_DIR  — set to repo root (harmless for collectors; used by rename_machine)
      _section_lines=() — reset before each call (collector contract)
    """
    with tempfile.NamedTemporaryFile(
        mode="r", suffix=".txt", delete=False
    ) as f:
        output_file = Path(f.name)
    try:
        zsh_script = f"""
set -e
OUTPUT_FILE={str(output_file)!r}
HOME={str(fake_home)!r}
SCRIPT_DIR={str(REPO_ROOT)!r}
_section_lines=()
source {str(SCRIPT)!r}
{collector_fn}
"""
        result = subprocess.run(
            ["zsh", "-c", zsh_script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"zsh collector {collector_fn!r} failed "
                f"(rc={result.returncode}):\n{result.stderr}"
            )
        return output_file.read_text(encoding="utf-8")
    finally:
        output_file.unlink(missing_ok=True)
```

**One-collector-per-subprocess rule** (from RESEARCH.md Pitfall 3):
- Always invoke `capture_zsh_section` with exactly ONE `collector_fn` per call.
- Each call gets a fresh zsh process. Never call two collectors in one `-c` script body — `_section_lines` is global in zsh and leaks between calls.

**stdout-vs-OUTPUT_FILE rule** (from RESEARCH.md Pitfall 2):
- Always read `output_file` (the temp file), never `result.stdout`.
- `capture_output=True` suppresses progress noise (`echo "  Collecting..."`) without discarding the section text.

---

### `tests/golden/*.golden.txt` (17 committed fixture files)

**Analog:** `tests/conftest.py` `catalog_repo` fixture — the pattern of committed text artifacts used as stable test inputs.

**Section-to-file mapping** (from `get_registry()` at `src/maccat/collectors/__init__.py`):

| Section title (exact) | Golden file | Input strategy |
|----------------------|-------------|----------------|
| Homebrew Packages | `homebrew-packages.golden.txt` | "not installed" fallback (stable static text) |
| App Store Applications | `app-store-applications.golden.txt` | "not installed" fallback |
| Setapp Applications | `setapp-applications.golden.txt` | "not installed" fallback (zsh hardcodes `/Applications/Setapp`) |
| Web-installed Applications | `web-installed-applications.golden.txt` | Python synthetic only — annotate `# zsh path hardcoded /Applications` |
| Claude Code Plugins | `claude-code-plugins.golden.txt` | synthetic `fake_home/.claude/plugins/installed_plugins.json` |
| Claude Code MCP Servers | `claude-code-mcp-servers.golden.txt` | synthetic `fake_home/.claude.json` (NO real secrets — transport only) |
| Claude Code Skills & Agents | `claude-code-skills-agents.golden.txt` | synthetic `fake_home/.claude/skills/` + `.claude/agents/` |
| Codex MCP Servers | `codex-mcp-servers.golden.txt` | synthetic `fake_home/.codex/config.toml` (TOML headers only) |
| OpenCode Plugins | `opencode-plugins.golden.txt` | synthetic `fake_home/.config/opencode/opencode.json` |
| OpenCode MCP Servers | `opencode-mcp-servers.golden.txt` | synthetic `fake_home/.config/opencode/opencode.json` |
| OpenCode Agents | `opencode-agents.golden.txt` | synthetic `fake_home/.config/opencode/agents/` |
| Gemini CLI Extensions | `gemini-extensions.golden.txt` | synthetic `fake_home/.gemini/extensions/` |
| Gemini CLI MCP Servers | `gemini-mcp-servers.golden.txt` | synthetic `fake_home/.gemini/config/mcp_config.json` |
| VS Code Extensions | `vscode-extensions.golden.txt` | synthetic `fake_home/.vscode/extensions/extensions.json` (file fallback, `code` CLI mocked absent) |
| Cursor Extensions | `cursor-extensions.golden.txt` | synthetic `fake_home/.cursor/extensions/extensions.json` (file fallback, `cursor` CLI mocked absent) |
| Google Chrome Extensions | `google-chrome-extensions.golden.txt` | synthetic `fake_home/Library/Application Support/Google/Chrome/Default/Extensions/` tree |
| Firefox Extensions | `firefox-extensions.golden.txt` | synthetic `fake_home/Library/Application Support/Firefox/` with `profiles.ini` + `extensions.json` |

**Reviewed-artifact policy:**
- These files are committed and diffed in code review.
- A plain `pytest` run MUST NOT modify any `.golden.txt` file.
- Update only via explicit `pytest --update-golden` after intentional format change.

---

### `tests/test_golden_parity.py` (parametrized parity test)

**Analog:** `tests/collectors/test_chrome.py` (patch.object on class attribute + tmp_path fixture)
**Structural analog:** RESEARCH.md Pattern 6 (parametrize over glob of golden files)

**Header pattern** (copy `from __future__ import annotations` convention from `tests/test_retention.py` lines 1–17):
```python
"""Golden-output parity suite (TEST-01, TEST-02).

Each parametrized case runs the Python collector for one section against the
same synthetic input used during golden capture, normalizes both outputs, and
asserts byte equality against the committed .golden.txt file.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
```

**Parametrize pattern** (from RESEARCH.md Pattern 6):
```python
GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN_FILES = sorted(GOLDEN_DIR.glob("*.golden.txt"))

@pytest.mark.parametrize(
    "golden_file",
    GOLDEN_FILES,
    ids=[f.stem for f in GOLDEN_FILES],   # failure reported as test_section_parity[section-name]
)
def test_section_parity(golden_file: Path, update_golden: bool) -> None:
    """Assert Python collector output matches golden fixture after normalization."""
    ...
    if update_golden:
        golden_file.write_text(normalized, encoding="utf-8")
        pytest.skip(f"Golden updated: {golden_file.name}")
    else:
        expected = golden_file.read_text(encoding="utf-8")
        assert normalized == expected, (
            f"Section '{golden_file.stem}' parity failed.\n"
            f"Run with --update-golden to refresh if format change is intentional."
        )
```

**patch.object pattern for path constants** (copy from `tests/collectors/test_claude.py` — same idiom used across all 400 existing tests):
```python
# Module-level path constant — patch to point at synthetic tmp_path tree
with patch.object(ClaudeCollector, "_PLUGINS_PATH", fake_plugins_json):
    result = ClaudeCollector().collect()

# Module-level constant (not class attribute) — use patch() with full dotted path
with patch("maccat.collectors.claude._CLAUDE_JSON", fake_claude_json):
    result = ClaudeCollector().collect()
```

**Fixture factory pattern** (per-section synthetic input — copy `_touch_catalog` helper style from `tests/test_retention.py` lines 24–28):
```python
def _make_claude_plugins_fixture(tmp_path: Path) -> Path:
    """Build synthetic fake_home/.claude/plugins/installed_plugins.json."""
    plugins_dir = tmp_path / ".claude" / "plugins"
    plugins_dir.mkdir(parents=True)
    plugins_json = plugins_dir / "installed_plugins.json"
    plugins_json.write_text(json.dumps({
        "plugins": {
            "my-plugin@registry": [{"version": "1.2.3"}]
        }
    }), encoding="utf-8")
    return tmp_path  # return fake_home root
```

**Webapps format-only caveat** (annotate in the test, per RESEARCH.md Q2):
```python
# web-installed-applications: zsh hardcodes /Applications — cannot synthetic-match zsh.
# This test verifies Python format correctness (section header + items present) only.
# zsh parity for this section is [ASSUMED] per 17-RESEARCH.md §Assumptions A1.
```

---

### `tests/test_safety_invariants.py` (consolidated 3-invariant safety suite)

**Analog:** `tests/test_retention.py` (logic source for invariants a and b) + `tests/test_identity.py` (logic source for invariant c)

This file consolidates — it does NOT introduce new logic. Copy the minimum test body from the existing tests; do not duplicate their full class suites.

**Header and marker pattern:**
```python
"""Explicit safety-invariant suite (TEST-03).

Co-locates the three destructive-op invariants as named, explicitly-tagged tests.
No new logic — extracted from test_retention.py and test_identity.py.

Invariants:
  (a) prune_old_archives NEVER deletes files with unparseable timestamps
  (b) retain_newest_per_host keeps ALL tied-newest files
  (c) rename_machine HARD refuses to clobber an existing folder
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from maccat.naming import make_catalog_filename
from maccat.retention import prune_old_archives, retain_newest_per_host
from maccat.identity import rename_machine

pytestmark = pytest.mark.safety_invariant  # explicit suite tag for -m filtering
```

**Invariant (a) — prune skips unparseable** (extract from `tests/test_retention.py` `test_unparseable_filename_never_deleted`, line 206):
```python
def test_prune_skips_unparseable_filename(tmp_path: Path) -> None:
    """INVARIANT (a): prune_old_archives NEVER deletes files with unparseable names.

    Source: test_retention.py::TestPruneOldArchives::test_unparseable_filename_never_deleted
    """
    archive = tmp_path / "archive"
    archive.mkdir()
    weird = archive / "old-notes.txt"
    weird.write_text("important notes", encoding="utf-8")

    with patch("maccat.retention.cutoff_yyyymmdd", return_value="20260601"):
        prune_old_archives(archive, archive_days=1)

    assert weird.exists(), "unparseable .txt in archive/ must never be deleted"
```

**Invariant (b) — retain keeps tied-newest** (extract from `tests/test_retention.py` `test_tied_newest_both_kept` + `test_tied_newest_two_hosts_tied`, lines 59–91):
```python
def test_retain_keeps_all_tied_newest(tmp_path: Path) -> None:
    """INVARIANT (b): retain_newest_per_host keeps ALL files with the max timestamp.

    Source: test_retention.py::TestRetainNewestPerHost::test_tied_newest_both_kept
            and test_tied_newest_two_hosts_tied
    """
    ts = "20260614120000"
    f_a = tmp_path / make_catalog_filename("alpha", ts)
    f_b = tmp_path / make_catalog_filename("beta", ts)
    f_a.write_text("", encoding="utf-8")
    f_b.write_text("", encoding="utf-8")

    retain_newest_per_host(tmp_path)

    assert f_a.exists(), "alpha tied-newest must be kept"
    assert f_b.exists(), "beta tied-newest must be kept"
    archive_dir = tmp_path / "archive"
    assert list(archive_dir.iterdir()) == [], "archive must be empty — nothing removed"
```

**Invariant (c) — rename refuses clobber** (extract from `tests/test_identity.py` `test_refuse_clobber_exits_nonzero`, lines 265–286):
```python
def test_rename_hard_refuses_clobber(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INVARIANT (c): rename_machine raises SystemExit when destination folder exists.

    Source: test_identity.py::TestRenameMachine::test_refuse_clobber_exits_nonzero
    """
    import sys

    old_dir = tmp_path / "OldName"
    old_dir.mkdir()
    (old_dir / make_catalog_filename("OldName", "20260614120000")).write_text(
        "x", encoding="utf-8"
    )
    new_dir = tmp_path / "NewName"
    new_dir.mkdir()  # already exists → must refuse

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with patch("builtins.input", side_effect=["1", "NewName"]):
        with pytest.raises(SystemExit):
            rename_machine(tmp_path)

    assert old_dir.is_dir(), "old folder untouched after refused rename"
    assert new_dir.is_dir(), "destination folder untouched after refused rename"
```

**Key constraint:** Add `safety_invariant` to `pytest` markers in `pyproject.toml`
`[tool.pytest.ini_options]` so `-m safety_invariant` works without a warning:
```toml
markers = ["safety_invariant: explicit destructive-op safety invariants (TEST-03)"]
```

---

### `tests/test_update_list_integrity.py` (TEST-04 zsh syntax check)

**Analog:** `tests/test_retention.py` subprocess-via-patch pattern; here a direct subprocess.run.

**Full file pattern** (from RESEARCH.md Q8):
```python
"""TEST-04: update-list.sh integrity check.

Verifies update-list.sh passes zsh -n (syntax check) at all times.
This test acts as a tripwire — if update-list.sh is accidentally modified
during Python development, CI fails here before any parity tests run.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def test_update_list_passes_zsh_syntax_check() -> None:
    """TEST-04: update-list.sh must pass `zsh -n` at milestone end."""
    result = subprocess.run(
        ["zsh", "-n", str(REPO_ROOT / "update-list.sh")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"update-list.sh failed zsh -n syntax check:\n{result.stderr}"
    )
```

**No fixtures needed** — reads a committed file at a fixed path. `REPO_ROOT` follows the same `Path(__file__).parent.parent` convention used by `tests/conftest.py` implicitly.

---

### `tests/conftest.py` (modify — add `--update-golden`)

**Analog:** `tests/conftest.py` itself (extend existing, lines 1–56)

**Addition pattern** (from RESEARCH.md Pattern 5 — add after the existing `catalog_repo` fixture):
```python
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
    return request.config.getoption("--update-golden")
```

**Integration with existing fixtures:** The existing `tmp_json`, `git_repo`, and `catalog_repo` fixtures are unchanged. The new `update_golden` fixture is available to all tests automatically (conftest.py is at `tests/` level).

---

### `.github/workflows/ci.yml` (new — no existing analog)

**No analog in repo** — this is the first CI file. Pattern comes from RESEARCH.md Q7 (verified standard GitHub Actions).

**Full workflow** (from RESEARCH.md Q7):
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: macos-latest   # zsh required for golden capture; macos-latest has it built-in
    strategy:
      matrix:
        # Two fixed seeds prove hash-order independence (proves no dict-iteration dependence
        # leaked past the LC_ALL=C sort -f -u shell-out in catalog/format.py).
        pythonhashseed: [0, 42]

    env:
      PYTHONHASHSEED: ${{ matrix.pythonhashseed }}

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dev dependencies
        run: |
          python -m venv venv
          ./venv/bin/pip install -e ".[dev]"

      - name: Lint (ruff)
        run: ./venv/bin/ruff check src tests

      - name: Type check (mypy)
        run: PYTHONPATH=src ./venv/bin/mypy --strict src/maccat

      - name: Run tests
        run: PYTHONPATH=src ./venv/bin/pytest -x -q

      - name: Check update-list.sh syntax (TEST-04)
        run: zsh -n update-list.sh
```

**Why `macos-latest`:** macOS runners have zsh at `/bin/zsh` by default. The golden-capture zsh subprocess requires real zsh; Linux runners would need an extra install step.

**Why seeds 0 and 42 (not `random`):** CI needs determinism for failure diagnosis. The default Python behavior (`PYTHONHASHSEED=random`) is implicitly tested on every local run. CI pins two seeds to guarantee that any hash-order regression fails consistently, not flappily.

---

## Shared Patterns

### Subprocess Convention
**Source:** `tests/conftest.py` lines 29–40 (`git_repo` fixture)
**Apply to:** `tests/golden/generate.py`, `tests/test_update_list_integrity.py`
```python
# Always: list form, capture_output=True, text=True, explicit timeout for zsh calls
result = subprocess.run(
    ["zsh", "-c", zsh_script],
    capture_output=True,
    text=True,
    timeout=30,
)
```

### patch.object on Collector Path Constants
**Source:** `tests/collectors/test_claude.py` (all 400 existing tests use this pattern)
**Apply to:** `tests/test_golden_parity.py` (for every HOME-based section)
```python
# Class attribute:
with patch.object(ClaudeCollector, "_PLUGINS_PATH", fake_path):
    result = ClaudeCollector().collect()

# Module-level constant:
with patch("maccat.collectors.claude._CLAUDE_JSON", fake_path):
    result = ClaudeCollector().collect()
```

### `_touch_catalog` Helper
**Source:** `tests/test_retention.py` lines 24–28 (identical helper in `tests/test_identity.py` is separate but identical)
**Apply to:** `tests/test_safety_invariants.py`
```python
def _touch_catalog(directory: Path, machine: str, timestamp: str) -> Path:
    p = directory / make_catalog_filename(machine, timestamp)
    p.write_text("", encoding="utf-8")
    return p
```

### Module Header Convention
**Source:** `tests/test_retention.py` lines 1–17 (docstring + `from __future__ import annotations`)
**Apply to:** All new test files
```python
"""One-sentence purpose. Which TEST-XX req this covers.

Key behaviors covered:
  - invariant/behavior 1
  - invariant/behavior 2
"""
from __future__ import annotations
```

### `pytestmark` Suite Tagging
**Source:** `tests/test_retention.py` (class-level marker style); here used at module level
**Apply to:** `tests/test_safety_invariants.py` exclusively
```python
pytestmark = pytest.mark.safety_invariant
```

### HOME Override in Zsh Subprocess
**Source:** RESEARCH.md Pitfall 1 (critical — verified by live test)
**Apply to:** `tests/golden/generate.py` every call to `capture_zsh_section`

The HOME assignment must appear in the zsh script body (inside the `-c` string), not just in `env=`:
```python
zsh_script = f"""
HOME={str(fake_home)!r}   # must be in script body, not env= dict
...
source {str(SCRIPT)!r}
{collector_fn}
"""
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.github/workflows/ci.yml` | config | — | No `.github/` directory exists yet; pattern supplied from research only |

---

## Critical Anti-Patterns (do NOT introduce these)

| Anti-Pattern | Where It Fails | Correct Pattern |
|---|---|---|
| Modifying `.golden.txt` outside `--update-golden` | Destroys reviewed-artifact property | Guard every write behind `if update_golden:` |
| `capture_zsh_section` reading `result.stdout` | stdout is progress messages, not section text | Always read `output_file` (temp file) |
| Calling two collectors in one zsh `-c` script | `_section_lines` leaks between calls | One `capture_zsh_section` call per collector |
| Omitting `HOME=` from zsh script body | Collector reads developer's real `~/.claude`, etc. | Set `HOME={str(fake_home)!r}` in script body |
| `sorted()` in normalize.py or test helpers | Diverges from `LC_ALL=C sort -f -u` | Do not sort — golden text is already sorted |
| Full-catalog golden (one file for everything) | Couples test to real machine brew/app state | Section-level goldens only (one per section) |
| webapps golden asserting item-by-item against zsh | `/Applications` hardcoded in zsh, not patchable | Python format-only / synthetic-Python-only for webapps |
| `import tests.golden.generate` at module level | Triggers zsh subprocess on every test collection | Import lazily, inside `if update_golden:` block only |

---

## Metadata

**Analog search scope:**
- `tests/conftest.py` (56 lines — fully read)
- `tests/test_retention.py` (363 lines — fully read)
- `tests/test_identity.py` (632 lines — fully read)
- `src/maccat/collectors/__init__.py` (71 lines — fully read)
- `17-CONTEXT.md` + `17-RESEARCH.md` — normalization spec, sourcing recipe, CI config
- `15-PATTERNS.md` — collector test patterns, patch.object convention

**Files scanned:** 6 source/test files + 3 planning documents
**Pattern extraction date:** 2026-06-14
