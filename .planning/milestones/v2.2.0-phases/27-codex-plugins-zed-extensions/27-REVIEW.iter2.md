---
phase: 27-codex-plugins-zed-extensions
reviewed: 2026-06-17T00:00:00Z
depth: standard
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
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 27: Code Review Report

**Reviewed:** 2026-06-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 27 adds the `Codex Plugins` section to `CodexCollector` and a new `ZedCollector`,
plus a title-constant refactor of `opencode.py` and a registry insertion for Zed.

The focus areas requested were verified and are clean:

- **(a) FMT-03 secret-safety** — PASS. No `tomllib` import, no `.mcp.json` reads (only
  docstring mentions). `_collect_plugins_via_cli` reads only `.name`/`.pluginId`;
  `_collect_plugins_via_toml` matches header lines only via `^\[plugins\."?([^"\]]+)"?\]$`,
  which cannot capture value lines. Verified empirically that secret-bearing value lines
  (`command`, `env`, `sk-...`) never leak. Tests assert this with a `SECRET_PATTERN` regex.
- **(c) determinism** — PASS. Both new sections are `raw=False`, so the orchestrator
  (`cli.py:327`) routes them through `flush_section` → `LC_ALL=C sort -f -u`. Collectors
  correctly do NOT pre-sort; dedup + stable order are guaranteed downstream.
- **(d) opencode refactor** — PASS, confirmed via git diff `1e068f6`. Three string literals
  replaced by equal-valued module constants (`_PLUGINS_TITLE`/`_MCP_TITLE`/`_AGENTS_TITLE`).
  Pure rename; emitted titles and output are byte-identical.
- **(f) registry ordering** — PASS. `ZedCollector()` inserted after `CursorCollector()`,
  matching the documented section order (16 Cursor → 17 Zed → 18 Chrome). Title uniqueness
  enforced by `test_section_titles.py` (19 unique titles).

Two never-raising defects were found (focus area **(b)**): both new collectors have an
unguarded code path that propagates an exception out of `collect()`. Because the orchestrator
loop (`cli.py:318-327`) does NOT wrap `collector.collect()` in try/except, any such exception
crashes the entire catalog run — directly violating the project's mandatory graceful-degradation
constraint ("a missing tool or browser must warn-and-continue"). Classified WARNING rather than
BLOCKER because both require an off-nominal trigger (exec failure mid-run / corrupted-schema
JSON) rather than normal operation, but both are real regressions against an explicit invariant.

All 34 phase tests pass.

## Warnings

### WR-01: `CodexCollector` CLI paths do not catch `OSError` from `subprocess.run` — violates never-raising contract

**File:** `src/maccat/collectors/codex.py:60-65` and `141-146`
**Issue:**
Both `_collect_via_cli` and `_collect_plugins_via_cli` call `subprocess.run(["codex", ...])`
guarded only by `shutil.which("codex")`. There is a TOCTOU window: `which` can return a path
while the subsequent `exec` fails (binary removed/replaced between check and run, broken symlink,
or a permission/`ETXTBSY` error). In those cases `subprocess.run` raises `FileNotFoundError`/
`OSError`, which propagates out of `collect()` and crashes the whole catalog run via the
unguarded orchestrator loop at `cli.py:319`.

This is inconsistent with the sibling `MasCollector`, which wraps the identical pattern in
`try/except OSError` with an explicit rationale comment ("TOCTOU / broken symlink / exec
failure: warn-and-continue per the project's graceful-degradation constraint instead of
crashing the CLI", `mas.py:79-82`). The docstrings here claim "never raises" (line 224), but
the exec-failure path does.

**Fix:** Wrap each `subprocess.run` and degrade to `[]` (matching the existing non-zero-exit
fallthrough), e.g.:
```python
try:
    result = subprocess.run(
        ["codex", "mcp", "list", "--json"],
        capture_output=True, text=True, shell=False,
    )
except OSError:
    return []
```
Apply the same guard in `_collect_plugins_via_cli`. Add a test mirroring the mas
TOCTOU case (`patch("subprocess.run", side_effect=OSError)`) asserting `collect()` does
not raise and falls through to the TOML path.

### WR-02: `ZedCollector` raises `AttributeError` when `index.json` top-level is valid JSON but not an object

**File:** `src/maccat/collectors/zed.py:43-48`
**Issue:**
`json.loads` is wrapped in `except (json.JSONDecodeError, OSError)`, but line 48 then calls
`data.get("extensions", {})` assuming `data` is a `dict`. If `index.json` contains *syntactically
valid* JSON that is a list, string, number, or `null` (e.g. a corrupted/truncated-to-`[]` file,
or a future schema change), `json.loads` succeeds — no `JSONDecodeError` — and `data.get(...)`
raises `AttributeError`. Verified: `[1,2,3]`, `"hello"`, `42`, `null` all raise. This propagates
out of `collect()` and crashes the catalog run.

The docstring (lines 32-33) explicitly promises degradation "when index.json is absent or
unreadable ... Never raises," and the spec calls for degrading "when absent/malformed." The
existing test `test_zed_malformed_index_returns_empty` only covers *unparseable* JSON
(`"{not: valid json"`), not the valid-but-wrong-type case, so the gap is untested.

Note the sibling collectors already guard this: `codex._collect_via_cli` uses
`isinstance(entries, list)` and `opencode._collect_mcp` uses `isinstance(mcp, dict)`. Zed is
the inconsistent one.

**Fix:** Add a top-level type guard after parsing:
```python
try:
    data = json.loads(_INDEX.read_text(encoding="utf-8"))
except (json.JSONDecodeError, OSError):
    return CollectorResult(sections=[Section(title=_TITLE, items=[])])
if not isinstance(data, dict):
    return CollectorResult(sections=[Section(title=_TITLE, items=[])])
```
Add a test feeding a top-level JSON array/scalar and asserting `items == []` with no exception.

## Info

### IN-01: Zed `manifest.get("name", ...)` / `get("version", ...)` are type-annotated `str` but unvalidated

**File:** `src/maccat/collectors/zed.py:58-59`
**Issue:**
`name: str = manifest.get("name", ext_id)` and `version: str = manifest.get("version", "")`
assert `str` via annotation, but a malformed manifest could supply an int/list. `emit_item`
would f-string it (no crash) but the value diverges from the declared type and from the
`name (version) [id]` format contract. Lower severity than WR-02 because it does not raise and
real Zed manifests always use strings.
**Fix:** Coerce or skip non-str values, e.g. `name = manifest.get("name") or ext_id` followed by
`if not isinstance(name, str): name = ext_id` (and similar for version), mirroring the
defensive `isinstance` checks used elsewhere in the codebase.

### IN-02: Codex plugin name/id fallback chaining can produce `name == id_` duplication-suppressed output

**File:** `src/maccat/collectors/codex.py:160-162`
**Issue:**
`name = entry.get("name", "") or entry.get("pluginId", "")` and
`id_ = entry.get("pluginId", "") or entry.get("name", "")`. When only one of the two fields is
present, both `name` and `id_` resolve to the same value, and `emit_item(name, "", id_)` would
emit `"foo [foo]"`. `emit_item` only suppresses the bracket when `name` is empty (the id-promotion
branch), not when `name == id_`, so a redundant `"foo [foo]"` line is possible. Not a correctness
bug for the installed plugin-less Codex (no entries), and harmless for catalog purposes, but
slightly noisy if a future Codex emits only one field.
**Fix (optional):** `id_ = entry.get("pluginId", "")` then `if id_ == name: id_ = ""` before
`emit_item`, to collapse `"foo [foo]"` → `"foo"`.

---

_Reviewed: 2026-06-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
