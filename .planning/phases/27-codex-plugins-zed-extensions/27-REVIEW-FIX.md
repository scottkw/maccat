---
phase: 27-codex-plugins-zed-extensions
fixed_at: 2026-06-17T00:00:00Z
review_path: .planning/phases/27-codex-plugins-zed-extensions/27-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 27: Code Review Fix Report

**Fixed at:** 2026-06-17T00:00:00Z
**Source review:** .planning/phases/27-codex-plugins-zed-extensions/27-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (Warning tier; `critical_warning` scope)
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: `CodexCollector` CLI paths do not catch `OSError` from `subprocess.run`

**Files modified:** `src/maccat/collectors/codex.py`, `tests/collectors/test_codex.py`
**Commit:** c4b09c9
**Applied fix:** Wrapped both `subprocess.run(["codex", ...])` calls — in
`_collect_via_cli` (MCP path) and `_collect_plugins_via_cli` (plugins path) — in
`try/except OSError`, returning `[]` on exec failure. This degrades to the TOML
fallback path (or empty section) instead of propagating `FileNotFoundError`/`OSError`
out of `collect()` and crashing the catalog run, mirroring the sibling `MasCollector`
pattern (`mas.py:79-82`). Added two tests using `patch("subprocess.run",
side_effect=OSError(...))` asserting `collect()` does not raise and falls through to
the `[mcp_servers.*]` / `[plugins.*]` TOML fallbacks.

### WR-02: `ZedCollector` raises `AttributeError` on valid-but-non-object JSON

**Files modified:** `src/maccat/collectors/zed.py`, `tests/collectors/test_zed.py`
**Commit:** 32f9392
**Applied fix:** Added an `isinstance(data, dict)` guard immediately after `json.loads`
(before the `data.get("extensions", {})` access). When `index.json` parses to a list,
scalar, or `null`, the collector now degrades to `items == []` instead of raising
`AttributeError`, mirroring the `isinstance` guards already used by sibling collectors
(`codex._collect_via_cli`, `opencode._collect_mcp`). Added a parametrized test feeding
`[1,2,3]`, `"hello"`, `42`, `null`, and `true`, asserting graceful empty output with no
exception.

## Skipped Issues

None — both in-scope findings were fixed.

## Out-of-Scope Notes (Info findings, not fixed)

- **IN-01** (`src/maccat/collectors/zed.py:58-59`): manifest `name`/`version` are
  annotated `str` but unvalidated. Info tier, out of `critical_warning` scope. Does not
  raise (would f-string a non-str value); left for a future pass.
- **IN-02** (`src/maccat/collectors/codex.py:160-162`): when only one of `name`/`pluginId`
  is present, both resolve to the same value and `emit_item(name, "", id_)` can emit
  `"foo [foo]"`. Info tier, out of `critical_warning` scope. Skipped: the suggested
  one-line guard (`if id_ == name: id_ = ""`) would change observable catalog output for
  the single-field case, which is a behavioral change better suited to its own scoped
  change than a code-review fix pass; current Codex (v0.46.0, no plugin system) never
  emits entries, so there is no live impact. Left as-is per the reviewer's "optional"
  classification.

## Verification

- Full test suite: 575 passed, 5 skipped (`PYTHONPATH=src python -m pytest`).
- `mypy --strict src/maccat`: clean (36 source files).
- `ruff check`: clean on all modified files.

---

_Fixed: 2026-06-17T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
