---
phase: 02-editor-collectors
verified: 2026-06-13T11:20:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 2: Editor Collectors — Verification Report

**Phase Goal:** A single run produces VS Code and Cursor extension sections in the catalog, read from the editors' extensions.json (with CLI as the preferred path when present).
**Verified:** 2026-06-13
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Produces a "VS Code Extensions" section listing each extension as `name (version) [id]`, via `code --list-extensions --show-versions` or extensions.json fallback | VERIFIED | Collector executed against real `~/.vscode/extensions/extensions.json`; produced 22 extension lines in exact `name (version) [id]` format. Header "VS Code Extensions" confirmed. CLI absent on this machine — extensions.json path exercised. |
| 2 | Produces a "Cursor Extensions" section in the same format via cursor CLI or extensions.json fallback | VERIFIED | Collector executed against real `~/.cursor/extensions/extensions.json`; produced 47 extension lines in exact `name (version) [id]` format. Header "Cursor Extensions" confirmed. 5 NLS placeholder extensions resolved to real display names. |
| 3 | When an editor is not installed (no CLI and no extensions.json), the section is still written with a "(none found)" note and the run continues | VERIFIED | Code path confirmed: `[[ ! -f "$ext_json" ]] && { echo "  NOTE: ..."; flush_section; return; }` — `flush_section` writes `(none found)` on empty buffer; `return` ensures run continues. Behavioral test with synthetic missing-dir confirmed output of section header + "(none found)". |
| 4 | Items within each editor section are stably sorted — two consecutive runs produce identical output | VERIFIED | Both collectors route output through `emit_item` → `flush_section` (which applies `LC_ALL=C sort -f -u`). Two consecutive VS Code runs produced empty `diff`. Two consecutive Cursor runs produced empty `diff`. |

**Score:** 4/4 truths verified

### Additional Must-Have Truths (from 02-01-PLAN frontmatter)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 5 | `update-list.sh` contains `resolve_vsc_ext_name`, `collect_vscode_extensions`, and `collect_cursor_extensions` function definitions | VERIFIED | `grep -n "^resolve_vsc_ext_name()\|^collect_vscode_extensions()\|^collect_cursor_extensions()"` → lines 495, 566, 673 |
| 6 | A `%key%` displayName placeholder resolves to its real string from `package.nls.json` — no raw `%key%` in output | VERIFIED | 5 NLS placeholder extensions in `~/.cursor/extensions` (incl. `%extension.title%` dotted key) all resolved: "Dev Containers", "HTML Preview", "IntelliCode API Usage Examples", "Remote Development", "Remote Explorer". Zero `%key%` strings in either collector's output. |
| 7 | An extension whose `package.json` has no displayName falls back to the extension ID as the name | VERIFIED | `resolve_vsc_ext_name`: `[[ -z "$dn" ]] && { echo "$ext_id"; return; }`. Behavioral test with synthetic missing-displayName fixture returned the ID unchanged. |
| 8 | Both collectors write their section via `write_section` + `emit_item` + `flush_section` and produce `(none found)` when no extensions exist | VERIFIED | Code confirmed at lines 572–573 (VSC), 679–680 (Cursor). `flush_section` writes `(none found)` on empty `_section_lines[]`. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `update-list.sh` | `resolve_vsc_ext_name`, `collect_vscode_extensions`, `collect_cursor_extensions` | VERIFIED | All three functions present (lines 495, 566, 673). File passes `zsh -n`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `collect_vscode_extensions` | `resolve_vsc_ext_name` | function call in file-fallback and CLI paths | VERIFIED | Lines 610, 636, 648 call `resolve_vsc_ext_name "$pkg_json" "$id"` |
| `collect_cursor_extensions` | `resolve_vsc_ext_name` | function call in file-fallback and CLI paths | VERIFIED | Lines 717, 743, 755 call `resolve_vsc_ext_name "$pkg_json" "$id"` |
| `collect_vscode_extensions` | `emit_item` / `flush_section` | Phase 1 helpers | VERIFIED | `emit_item` called at line 614 (CLI path), 637, 648 (file path); `flush_section` at 616, 654 |
| `collect_cursor_extensions` | `emit_item` / `flush_section` | Phase 1 helpers | VERIFIED | `emit_item` called at line 721 (CLI path), 744, 755 (file path); `flush_section` at 723, 761 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `collect_vscode_extensions` | `_section_lines[]` | `~/.vscode/extensions/extensions.json` via jq | Yes — 22 live entries confirmed in execution | FLOWING |
| `collect_cursor_extensions` | `_section_lines[]` | `~/.cursor/extensions/extensions.json` via jq | Yes — 47 live entries confirmed in execution | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| VS Code collector produces real extension lines | Executed against `~/.vscode/extensions/extensions.json` | 22 lines in `name (version) [id]` format | PASS |
| Known entry "Auto Rename Tag (0.1.10)" present | `grep -F "Auto Rename Tag" output` | Found | PASS |
| No raw `%key%` in VS Code output | `grep -E '%[A-Za-z]'` | 0 matches | PASS |
| No literal `(null)` or `[null]` in VS Code output | `grep "(null)"` / `grep "[null]"` | 0 matches each | PASS |
| Cursor collector produces 47 extension lines | Executed against `~/.cursor/extensions/extensions.json` | 47 lines in correct format | PASS |
| NLS placeholder `%extension.title%` resolved | `grep "IntelliCode API Usage Examples"` in Cursor output | Found | PASS |
| NLS placeholder `%displayName%` (Dev Containers) resolved | `grep "Dev Containers"` in Cursor output | Found | PASS |
| VS Code determinism: two runs diff | `diff run1.txt run2.txt` | Empty (identical) | PASS |
| Cursor determinism: two runs diff | `diff run1.txt run2.txt` | Empty (identical) | PASS |
| `generate_catalog` does not call collectors | `awk '/^generate_catalog/,/^\}/' ... \| grep collect_` | 0 matches | PASS |

### Probe Execution

No declared probes for this phase. Phase 2 used an ephemeral self-test (02-02-PLAN) that was not committed. Verifier re-ran the functional checks directly.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| VSC-01 | 02-01-PLAN | Catalog VS Code extensions (name + version + ID) via `code --list-extensions --show-versions`, falling back to `extensions.json` | SATISFIED | `collect_vscode_extensions` implemented; CLI path uses `code --list-extensions --show-versions`; file-fallback reads `~/.vscode/extensions/extensions.json`; 22 real extensions confirmed in output with correct format. Marked complete in REQUIREMENTS.md. |
| CUR-01 | 02-01-PLAN | Catalog Cursor extensions (name + version + ID) via the `cursor` CLI, falling back to `extensions.json` | SATISFIED | `collect_cursor_extensions` implemented; CLI path uses `cursor --list-extensions --show-versions`; file-fallback reads `~/.cursor/extensions/extensions.json`; 47 real extensions confirmed, 5 NLS placeholders resolved. Marked complete in REQUIREMENTS.md. |

VSC-01 and CUR-01 are both marked `[x]` complete in REQUIREMENTS.md traceability table — consistent with implementation evidence.

### Anti-Patterns Found

Scanned files modified in this phase (update-list.sh, commits 45af087–48c4349).

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `update-list.sh` | 492, 531 | `getpath` appears in comments inside `resolve_vsc_ext_name` | INFO | Comments only; actual live code uses `.[$k]` — not a bug. The comment text explicitly says "NOT getpath". |

No TBD, FIXME, XXX, or unresolved debt markers found in the modified lines.

### Post-Review Fixes Confirmed in Live Code

The code review (02-REVIEW.md) identified 3 warnings and 1 info item. All 4 were fixed per 02-REVIEW-FIX.md. Each fix was verified against the live code:

| Fix | Status | Evidence |
|-----|--------|---------|
| **WR-01**: `// ""` null-coalescing on `.identifier.id`, `.version`, `.relativeLocation` in file-fallback path | VERIFIED | Lines 631–633 (VSC), 738–740 (Cursor) — all three fields use `// ""` |
| **WR-02**: plutil `scan_idx` index-loop fallback for `relativeLocation` in CLI path | VERIFIED | Lines 596–604 (VSC), 703–711 (Cursor) — `scan_idx` loop present in both |
| **WR-03**: `[[ "$id" == "$version" ]] && continue` guard for no-`@` CLI lines | VERIFIED | Lines 586 (VSC), 693 (Cursor) — guard present in both collectors |
| **IN-01**: `line=""` declared `local` in both collectors | VERIFIED | Lines 569 (VSC), 676 (Cursor) — `line=""` in `local` declaration of both |

### Human Verification Required

None. All required behaviors were verifiable programmatically by exercising the collectors against real `~/.vscode/extensions` and `~/.cursor/extensions` data.

---

## Summary

Phase 2 goal achieved. All four ROADMAP success criteria are observably true in the codebase:

1. **VS Code section**: `collect_vscode_extensions` executes the extensions.json fallback path on this machine (no CLI installed), reading `~/.vscode/extensions/extensions.json` via jq, resolving display names through `resolve_vsc_ext_name`, and producing 22 correctly-formatted `name (version) [id]` lines in a "VS Code Extensions" section.

2. **Cursor section**: `collect_cursor_extensions` produces 47 correctly-formatted lines. Five extensions with `%key%` NLS placeholders (including `%extension.title%` with a literal dot) are resolved to their real display names via `.[$k]` jq lookup. Zero raw `%key%` strings leak into output.

3. **Graceful degradation**: When `extensions.json` is absent, the section header is still written and `flush_section` emits `(none found)`. Code path confirmed; behavioral test confirmed. Run continues with `return` (not `exit`).

4. **Stable sort / determinism**: Output routes through `flush_section` → `LC_ALL=C sort -f -u`. Two consecutive runs of both collectors produce empty `diff`.

All four post-review fixes (WR-01 null-coalescing, WR-02 plutil CLI fallback, WR-03 `@` guard, IN-01 `local line`) are confirmed in the live code at their documented line numbers. `generate_catalog` contains zero calls to the new collectors (Phase 5 wiring is correctly deferred). `zsh -n update-list.sh` exits 0.

---

_Verified: 2026-06-13T11:20:00Z_
_Verifier: Claude (gsd-verifier)_
