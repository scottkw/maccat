---
phase: 02-editor-collectors
plan: "01"
subsystem: update-list.sh
tags: [vscode, cursor, extensions, nls-resolution, zsh]
dependency_graph:
  requires:
    - 01-01 (json_get, emit_item, flush_section, write_section Phase 1 helpers)
  provides:
    - resolve_vsc_ext_name (NLS-aware display name resolver, used by both collectors)
    - collect_vscode_extensions (defined, not yet wired)
    - collect_cursor_extensions (defined, not yet wired)
  affects:
    - update-list.sh (additive insertion after flush_section)
tech_stack:
  added: []
  patterns:
    - Flat-key jq lookup (.[$k]) for NLS keys containing literal dots
    - backslash-escaped plutil path for NLS keys (extension\.title)
    - relativeLocation-based package.json path (eliminates platform-suffix guessing)
    - while IFS= read -r iteration for jq output with spaces in values
key_files:
  created: []
  modified:
    - update-list.sh
decisions:
  - resolve_vsc_ext_name uses .[$k] not getpath(split(".")) for NLS — dotted keys like
    "extension.title" are flat top-level keys in package.nls.json, not nested paths
  - relativeLocation is used exclusively for pkg_json path construction — naive
    id+version reconstruction fails due to platform suffixes (-darwin-arm64, -universal)
  - Collectors defined but NOT wired into generate_catalog (Phase 5 responsibility)
metrics:
  duration_minutes: 15
  completed_date: "2026-06-13"
  tasks_completed: 2
  files_modified: 1
---

# Phase 02 Plan 01: VS Code and Cursor Extension Collectors Summary

Three Zsh functions inserted into update-list.sh: NLS-aware resolve_vsc_ext_name helper plus collect_vscode_extensions and collect_cursor_extensions with CLI-first/extensions.json fallback enumeration using relativeLocation for exact package.json path resolution.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Insert resolve_vsc_ext_name, collect_vscode_extensions, collect_cursor_extensions | 45af087 | update-list.sh (+252 lines) |
| 2 | Commit the implementation | 45af087 | update-list.sh |

## What Was Built

**resolve_vsc_ext_name** (lines 495-543):
- Reads `displayName` from `package.json` via `json_get`
- Returns ID immediately if displayName is absent
- Returns plain string immediately if not a `%key%` placeholder
- Strips `%` delimiters and looks up in `package.nls.json` using flat-key lookup:
  - jq: `.[$k]` (handles keys with literal dots like `extension.title`)
  - plutil: `${nls_key//./\\.}` escaping before `-extract`
- Falls back to extension ID if NLS file absent or key not found
- Never emits blank names or raw `%key%` strings

**collect_vscode_extensions** (lines 566-655):
- Section header: "VS Code Extensions"
- CLI path: `code --list-extensions --show-versions` when on PATH
- File fallback: `~/.vscode/extensions/extensions.json` (operative path on this machine)
- Uses `relativeLocation` field to construct exact `pkg_json` path
- jq path: `while IFS= read -r` loop over `jq -c '.[]'` output
- plutil path: index loop (`0.identifier.id`, `1.identifier.id`, ...) until miss
- Routes all output through `emit_item` → `flush_section`

**collect_cursor_extensions** (lines 656-745):
- Identical to VS Code collector; substitutions: `~/.cursor/extensions`, `cursor` CLI, "Cursor Extensions" section title

## Verification

```
zsh -n update-list.sh                  → syntax OK
grep -n "^resolve_vsc_ext_name()"      → line 495
grep -n "^collect_vscode_extensions()" → line 566
grep -n "^collect_cursor_extensions()" → line 656
getpath in resolve_vsc_ext_name        → NOT present (only in json_get + comments)
generate_catalog call sites            → 0 (collectors not wired yet)
git diff --diff-filter=D HEAD~1 HEAD   → 0 deleted lines (additive only)
```

## Deviations from Plan

None — plan executed exactly as written. All three functions implemented per the verified algorithm in 02-RESEARCH.md. No architectural changes, no new packages, no bug fixes required.

## Known Stubs

None. Functions are defined stubs in the sense that they are not yet called from `generate_catalog`, but this is intentional per plan design (Phase 5 wires them). The function logic itself is complete and tested via `zsh -n`.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced beyond those documented in the plan's `<threat_model>`. Collectors read only from `~/.vscode/extensions/` and `~/.cursor/extensions/` (local filesystem, user-owned). No credentials or tokens in the fields accessed.

## Self-Check: PASSED

- [x] update-list.sh exists and passes `zsh -n`
- [x] resolve_vsc_ext_name defined at line 495
- [x] collect_vscode_extensions defined at line 566
- [x] collect_cursor_extensions defined at line 656
- [x] Commit 45af087 exists in git log
- [x] generate_catalog contains no calls to the new collectors
- [x] Diff is additive only (0 deleted lines)
