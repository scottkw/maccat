---
phase: 13-package-foundation-output-format
verified: 2026-06-14T21:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 13: Package Foundation & Output Format — Verification Report

**Phase Goal:** A runnable Python package skeleton exists with the complete output format layer — every downstream collector and test can be built on a stable, byte-verified foundation.
**Verified:** 2026-06-14T21:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `src/maccat/` imports cleanly with zero third-party runtime deps; `python -c "import maccat"` succeeds | VERIFIED | `PYTHONPATH=src ./venv/bin/python -c "import maccat; print(maccat.__version__)"` → `OK: 1.0.0`; `pyproject.toml` has `requires-python = ">=3.11"` and no `[project.dependencies]` section |
| 2 | `flush_section()` shells out to `LC_ALL=C sort -f -u` and produces byte-identical output to the equivalent zsh call for mixed-case, non-ASCII, and punctuation-containing names — never Python `sorted()` | VERIFIED | Live parity check confirmed `flush_section(['b','A','a','C'])` output equals `printf '%s\n' b A a C \| LC_ALL=C sort -f -u`; `grep -c 'sorted(' format.py` → 0; `format.py` uses `subprocess.run(["sort", "-f", "-u"], env={LC_ALL:C})` |
| 3 | `CatalogWriter` writes section headers, item lines, and separators byte-identical to the zsh `write_section` + `emit_item` pattern (verified by `xxd` at section boundaries) | VERIFIED | `write_section("Homebrew Packages")` produces exactly `0a 48 6f 6d 65 62 72 65 77 20 50 61 63 6b 61 67 65 73 0a 2d×36 0a`; `test_write_section_bytes_exact` passes; separator confirmed as exactly `"-" * 36` |
| 4 | Chrome `__MSG_…__` and VS Code `%nls%` placeholder names resolve correctly using the same ID/displayName fallback logic as the zsh script | VERIFIED | `chrome_ext_name` resolves `__MSG_extName__` → `"Real Name"`, case-insensitive `__MSG_EXTNAME__` → `"Case Folded"`; `resolve_vsc_ext_name` resolves `%extension.title%` → `"Real Name"` via flat `.get()`; `json_get` returns `""` for the same dotted key (Pitfall 3 confirmed); `grep -c 'json_get.*nls' vsc_name.py` → 0 |
| 5 | Running `python3 --version` below 3.11 prints a clear, actionable error and exits — never hangs on the macOS CLT install dialog | VERIFIED | `__main__.py` line 5: `if sys.version_info < (3, 11): sys.exit(...)` is the FIRST executable code after `import sys`; message includes `brew install python@3.11`, `https://python.org/downloads/`, and explicit warning about `/usr/bin/python3`; zero top-level `from maccat.*` imports confirmed by grep |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | name=maccat, requires-python>=3.11, no runtime deps | VERIFIED | Present; `requires-python = ">=3.11"`; no `[project.dependencies]` key; hatchling build backend |
| `.python-version` | "3.11" pin for pyenv | VERIFIED | Present |
| `src/maccat/__init__.py` | `__version__ = "1.0.0"` only | VERIFIED | Contains docstring + `__version__ = "1.0.0"`, no imports, no side effects |
| `src/maccat/__main__.py` | Version guard as first executable code | VERIFIED | `import sys` then `if sys.version_info < (3, 11): sys.exit(...)` at lines 3-15; deferred `from maccat.cli import run` inside `main()` |
| `src/maccat/catalog/__init__.py` | Package stub | VERIFIED | Present |
| `src/maccat/helpers/__init__.py` | Package stub | VERIFIED | Present |
| `src/maccat/catalog/format.py` | `emit_item`, `flush_section`, `version_sort_tail` | VERIFIED | All three functions implemented; subprocess sort; no `sorted()` or `shell=True` |
| `src/maccat/catalog/writer.py` | `CatalogWriter` context manager | VERIFIED | Atomic `mkstemp` + `rename`; `write_section` produces exact byte sequence; `write_lines` adds one `\n` per line |
| `src/maccat/helpers/json_io.py` | `json_get()` — dotted-path, never raises | VERIFIED | Implements dotted-path traversal; catches `(json.JSONDecodeError, OSError, UnicodeDecodeError)`; NLS warning in docstring |
| `src/maccat/helpers/chrome_name.py` | `chrome_ext_name()` — `__MSG_key__` resolution | VERIFIED | Grandparent dir as ext_id; case-insensitive `{k.lower(): v}` dict iteration; first-match wins (head -1 parity) |
| `src/maccat/helpers/vsc_name.py` | `resolve_vsc_ext_name()` — `%nls_key%` flat lookup | VERIFIED | Uses `nls.get(nls_key)` directly; never calls `json_get` for NLS lookup |
| `tests/__init__.py` | Package init | VERIFIED | Present |
| `tests/test_format.py` | 20 unit tests for format layer | VERIFIED | 20 tests; includes parity test (`test_sort_parity_with_subprocess`) calling sort directly |
| `tests/test_writer.py` | 8 byte-level tests for CatalogWriter | VERIFIED | 8 tests; `test_write_section_bytes_exact` asserts byte-identical output |
| `tests/conftest.py` | `tmp_json` fixture factory | VERIFIED | `@pytest.fixture()` named `tmp_json`; used by `test_helpers.py` |
| `tests/test_helpers.py` | 26 tests covering all 3 helpers | VERIFIED | 26 tests; Pitfall 3 demonstrated in `test_nls_placeholder_with_dotted_key_resolved_flat` |
| `tests/golden/.gitkeep` | Directory scaffold for Phase 17 | VERIFIED | Present; empty file; directory tracked in git |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/maccat/catalog/format.py` | `/usr/bin/sort` (LC_ALL=C -f -u) | `subprocess.run(["sort", "-f", "-u"], env={LC_ALL:C})` | WIRED | Confirmed at lines 59-65; `shell=False` (default); env override present |
| `src/maccat/catalog/writer.py` | `tempfile.mkstemp` | atomic tmp + rename in `__exit__` | WIRED | Confirmed at lines 39-57; `mkstemp` count = 2; rename on success, unlink on exception |
| `src/maccat/helpers/chrome_name.py` | `src/maccat/helpers/json_io.py` | `from maccat.helpers.json_io import json_get` | WIRED | Line 6; used for manifest `name` and `default_locale` lookups |
| `src/maccat/helpers/vsc_name.py` | `src/maccat/helpers/json_io.py` | `from maccat.helpers.json_io import json_get` (displayName only) | WIRED | Line 6; NLS lookup uses `json.loads().get()` directly — NOT `json_get` (Pitfall 3 correct) |
| `src/maccat/__main__.py` | `sys.version_info` | guard before any maccat.* import | WIRED | Line 5 — first executable code after `import sys`; pattern `sys.version_info < (3, 11)` |

### Data-Flow Trace (Level 4)

Not applicable — this phase implements utility functions and helpers, not components that render dynamic data from a database or external source. The output flows are: string inputs → `subprocess.run(sort)` → list of strings, and string inputs → `CatalogWriter._fh.write()` → file bytes. These are verified by the byte-level tests.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `import maccat` succeeds | `PYTHONPATH=src ./venv/bin/python -c "import maccat; print(maccat.__version__)"` | `OK: 1.0.0` | PASS |
| `flush_section` byte-parity | Python vs `sort -f -u` subprocess | `['A', 'b', 'C']` matches both | PASS |
| `CatalogWriter.write_section` bytes | hex dump assertion | `0a 48 6f...2d×36 0a` exact match | PASS |
| Chrome `__MSG__` resolution | `chrome_ext_name` with `__MSG_EXTNAME__` | `"Case Folded"` (case-insensitive) | PASS |
| VS Code `%nls%` flat key resolution | `resolve_vsc_ext_name` with `%extension.title%` | `"Real Name"` via flat `.get()` | PASS |
| Full test suite | `PYTHONPATH=src ./venv/bin/pytest tests/ -q` | `59 passed in 0.12s` | PASS |

### Probe Execution

No probes declared. Phase goal verified via direct import checks and test suite execution above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PKG-01 | 13-01 | Zero third-party runtime dependencies | SATISFIED | `pyproject.toml` has no `[project.dependencies]`; `import maccat` succeeds from stdlib-only package |
| PKG-02 | 13-01 | Python 3.11+ fail-fast guard; never hangs on CLT dialog | SATISFIED | `__main__.py` line 5: `if sys.version_info < (3, 11): sys.exit(...)` as first executable code; deferred maccat.* imports confirmed |
| CAT-02 | 13-02 | `name (version) [id]` FMT-01 format + degradation rules | SATISFIED | `emit_item` implements all 7 FMT-01 cases including id-as-name promotion; 8 test cases pass |
| CAT-03 | 13-02 | `LC_ALL=C sort -f -u` shell-out; never Python `sorted()` | SATISFIED | `flush_section` uses `subprocess.run(["sort", "-f", "-u"], env={LC_ALL:C})`; `grep -c 'sorted(' format.py` → 0 |
| CAT-04 | 13-03 | Chrome `__MSG__` and VS Code `%nls%` resolved same as zsh | SATISFIED | Both helpers implement correct fallback chains; Pitfall 3 (flat key vs dotted traversal) demonstrated and tested |
| CAT-07 | 13-02 | Section separators byte-identical to zsh catalog | SATISFIED | `"-" * 36 + "\n"` with leading `\n`; confirmed by `test_write_section_bytes_exact` hex assertion |

All 6 requirement IDs claimed by the phase plans are accounted for. No orphaned requirements found for Phase 13 in REQUIREMENTS.md.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/maccat/__main__.py` | 20 | `from maccat.cli import run` — forward ref to Phase 16 module | Info | Intentional stub; raises `NotImplementedError("Phase 16")`; noted in verification environment notes as accepted |

No `TBD`, `FIXME`, or `XXX` markers found. No `sorted()` in `format.py`. No `shell=True` anywhere in the format layer. No empty/stub return values in implementation files (all functions are fully implemented). The `NotImplementedError("Phase 16")` in `__main__.py` is the accepted forward-reference stub documented in the verification environment notes.

### Human Verification Required

None. All success criteria are mechanically verifiable and were verified above.

### Gaps Summary

None. All 5 success criteria verified against the actual codebase. 59/59 tests pass. All 6 requirement IDs (PKG-01, PKG-02, CAT-02, CAT-03, CAT-04, CAT-07) are satisfied with evidence in the code.

---

_Verified: 2026-06-14T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
