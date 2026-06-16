---
phase: 13-package-foundation-output-format
plan: "03"
subsystem: helpers
tags:
  - json
  - chrome-extensions
  - vscode-extensions
  - name-resolution
  - tdd
dependency_graph:
  requires:
    - 13-01 (helpers/__init__.py package stub)
  provides:
    - json_get — dotted-path JSON key extractor used by chrome_name and vsc_name
    - chrome_ext_name — __MSG_key__ resolver for Chrome extensions
    - resolve_vsc_ext_name — %nls_key% flat-key resolver for VS Code/Cursor extensions
    - tmp_json fixture factory for all path-based tests
    - tests/golden/ directory scaffold for Phase 17
  affects:
    - Phase 15 collectors (all three helpers are called per-extension during enumeration)
    - Phase 17 parity tests (tests/golden/ directory scaffold)
tech_stack:
  added: []
  patterns:
    - dotted-path JSON traversal via json.loads (replaces jq+plutil subprocess chain)
    - case-insensitive dict lookup {k.lower(): v} for Chrome messages.json
    - flat .get(key) for VS Code NLS (never json_get for NLS — Pitfall 3)
    - TDD RED/GREEN with pytest fixtures and directory structure helpers
key_files:
  created:
    - src/maccat/helpers/json_io.py
    - src/maccat/helpers/chrome_name.py
    - src/maccat/helpers/vsc_name.py
    - tests/conftest.py
    - tests/golden/.gitkeep
  modified:
    - tests/test_helpers.py (new file, committed in two commits: RED then GREEN+style)
decisions:
  - "json_get uses cur.get(part) not cur[part] — avoids KeyError; returns default on None sentinel"
  - "chrome_name len(name) > len('__MSG__') guard mirrors zsh ?* glob (non-empty key)"
  - "vsc_name uses json.loads().get(nls_key) for NLS — never json_get — flat keys with literal dots"
metrics:
  duration_seconds: 191
  completed_date: "2026-06-14"
  tasks_completed: 2
  files_created: 6
---

# Phase 13 Plan 03: Name-Resolution Helpers Summary

JSON extractor, Chrome __MSG__ resolver, and VS Code %nls% resolver — three stdlib-only helpers
with full TDD coverage including explicit Pitfall 3 (NLS dotted-key) demonstration test.

## What Was Built

**`src/maccat/helpers/json_io.py`** — `json_get(file, key, default="") -> str`
- Replaces the zsh jq+plutil subprocess chain entirely with `json.loads()`
- Dotted-path traversal: `"author.name"` → `data["author"]["name"]`
- Never raises: catches `(json.JSONDecodeError, OSError, UnicodeDecodeError)`
- Docstring explicitly warns against using for VS Code NLS lookups (Pitfall 3)

**`src/maccat/helpers/chrome_name.py`** — `chrome_ext_name(manifest_path) -> str`
- Resolves `__MSG_extName__` placeholders via `_locales/<locale>/messages.json`
- Case-insensitive lookup: `{k.lower(): v for k, v in messages.items()}`
- Grandparent dir (`manifest_path.parent.parent.name`) is the extension ID
- Fallback chain: resolved message → ext_id (never blank, never raw placeholder)

**`src/maccat/helpers/vsc_name.py`** — `resolve_vsc_ext_name(pkg_json, ext_id) -> str`
- Resolves `%extension.title%` placeholders via `package.nls.json`
- FLAT key lookup: `nls.get(nls_key)` — never `json_get(nls_file, nls_key)`
- Keys like `"extension.title"` are top-level flat keys, not nested paths
- Fallback chain: resolved string → ext_id (never blank, never raw placeholder)

**`tests/conftest.py`** — `tmp_json` fixture factory
- `_write(data: dict, filename: str = "test.json") -> Path`
- Used by test_helpers.py and available to all future test files

**`tests/golden/.gitkeep`** — Phase 17 fixture directory scaffold

## Test Coverage

54 total tests passing (26 new in test_helpers.py + 28 from prior plans):
- 11 `json_get` tests: missing file, empty key, dotted traversal, non-string leaf, malformed JSON
- 8 `chrome_ext_name` tests: plain name, empty name, MSG placeholder, case-insensitive, missing locales, absent key, empty key guard, non-default locale
- 7 `resolve_vsc_ext_name` tests: plain name, missing displayName, dotted flat key (with Pitfall 3 demonstration), missing NLS key, missing NLS file, empty percent guard, simple key

## Pitfall 3 Demonstration

`test_nls_placeholder_with_dotted_key_resolved_flat` explicitly asserts both:
1. `json_get(nls_file, "extension.title")` returns `""` — dotted traversal fails on flat key
2. `json.loads(nls_file.read_text()).get("extension.title")` returns `"Real Name"` — flat lookup works
3. `resolve_vsc_ext_name(pkg_json, ext_id)` returns `"Real Name"` — function uses the correct path

## TDD Gate Compliance

- RED commit: `9f42955` — `test(13-03): add failing tests for chrome_ext_name and resolve_vsc_ext_name`
- GREEN commit: `c14db9b` — `feat(13-03): implement chrome_name.py and vsc_name.py helpers`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Unused `pytest` import and unsorted imports in test_helpers.py**
- **Found during:** Post-task ruff lint check
- **Issue:** `import pytest` was included in test_helpers.py but not used (conftest.py provides fixtures without explicit pytest import in test file); ruff also flagged import ordering
- **Fix:** Removed `import pytest`; ran `ruff check --fix` to sort import block
- **Files modified:** `tests/test_helpers.py`
- **Commit:** `1be8855`

## Known Stubs

None — all helpers are fully implemented with no placeholder returns.

## Threat Flags

None — helpers are read-only utilities that extract name fields from extension manifests. No new network endpoints, auth paths, file writes, or schema changes introduced.

## Self-Check: PASSED
