---
phase: 27-codex-plugins-zed-extensions
reviewed: 2026-06-17T00:00:00Z
depth: standard
iteration: 2
files_reviewed: 7
files_reviewed_list:
  - src/maccat/collectors/codex.py
  - src/maccat/collectors/zed.py
  - src/maccat/collectors/opencode.py
  - src/maccat/collectors/__init__.py
  - tests/collectors/test_codex.py
  - tests/collectors/test_zed.py
  - tests/collectors/test_section_titles.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
---

# Phase 27: Code Review Report (Iteration 2)

**Reviewed:** 2026-06-17T00:00:00Z
**Depth:** standard
**Status:** clean

## Summary

Re-review of iteration 1 fixes for WR-01 (codex `subprocess.run` exec-failure handling)
and WR-02 (Zed non-object JSON handling). Both fixes are correct and complete; no new
defects were introduced. FMT-03 (identity-only, no secret leakage) remains intact, and the
OpenCode title-constant refactor is output-neutral. All reviewed files meet quality
standards. No new findings.

### Verification of iteration 1 fixes

**WR-01 (codex never raises on exec failure — BOTH subprocess sites): CONFIRMED FIXED.**
- `_collect_via_cli` (codex.py:60-70): `subprocess.run` wrapped in `try/except OSError`,
  returns `[]` on failure, falls through to the MCP TOML grep at line 131.
- `_collect_plugins_via_cli` (codex.py:146-156): identical `try/except OSError` guard,
  returns `[]`, falls through to the `[plugins.*]` TOML grep at line 220.
- `except OSError` is the complete exception set for this call shape: `FileNotFoundError`
  and `PermissionError` (TOCTOU after `shutil.which`, broken symlink, `ETXTBSY`) are all
  OSError subclasses; no `timeout=` is set so `TimeoutExpired` cannot occur; the fixed
  list argv with `shell=False` cannot raise `ValueError`.
- Both handlers return `[]` (matching the `list[str]` return type) — no type or
  control-flow regression; the downstream fall-through to TOML operates correctly on the
  empty result.
- New tests cover both sites: `test_cli_oserror_falls_through_to_toml` (test_codex.py:223)
  and `test_plugins_cli_oserror_falls_through_to_toml` (test_codex.py:238), each asserting
  `collect()` does not raise and the TOML fallback produces output.

**WR-02 (Zed never raises on any json.loads result type): CONFIRMED FIXED.**
- zed.py:50-51 guards `isinstance(data, dict)` after `json.loads`, before any `.get()` call.
- The guard covers every possible `json.loads` return type (dict, list, str, int, float,
  bool, None); all non-dict values degrade to `items=[]` instead of raising `AttributeError`.
- New parametrized test `test_zed_non_object_json_returns_empty` (test_zed.py:141) exercises
  `[1,2,3]`, `"hello"`, `42`, `null`, `true` — list, scalar, null, and bool all covered.

### Invariant and neutrality checks

- **FMT-03 intact:** CLI paths read identity fields only (`.name`, `.type`, `.pluginId`);
  TOML fallbacks regex-match section-header lines only — no `tomllib`, no value lines, no
  `.mcp.json` reads. Secret-grep regression tests (`SECRET_PATTERN`) pass for both the MCP
  and plugins TOML output.
- **OpenCode title refactor output-neutral:** module-level `_PLUGINS_TITLE` / `_MCP_TITLE`
  / `_AGENTS_TITLE` resolve to the exact prior strings; each sub-collector assigns the
  constant to a local `title` and emits it unchanged. Confirmed by passing
  `test_section_titles.py` (19-title uniqueness + manual-checklist fallthrough).
- **Registry ordering:** `ZedCollector()` remains positioned after `CursorCollector()`
  (16 Cursor → 17 Zed → 18 Chrome); unchanged this iteration.

### Tooling status

- `pytest` on the 3 changed test files: 41 passed.
- `pytest tests/collectors/` (full regression suite): 203 passed.
- `mypy --strict` on the 3 source files: clean.
- `ruff check` on the 3 source files: clean.

## Narrative Findings (AI reviewer)

No new Critical, Warning, or Info findings.

Accepted carry-over items IN-01 (unvalidated `str` manifest/entry fields, zed.py:64-65)
and IN-02 (possible `foo [foo]` when name == id, codex.py:170-172) were confirmed still
present by design and were not re-flagged, per the review scope.

---

_Reviewed: 2026-06-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard (iteration 2)_
