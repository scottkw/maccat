---
phase: 02-editor-collectors
reviewed: 2026-06-13T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - update-list.sh
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: fixes_applied
---

# Phase 2: Editor Collectors — Code Review

**Reviewed:** 2026-06-13
**Depth:** standard
**Files Reviewed:** 1 (three new functions in `update-list.sh`: `resolve_vsc_ext_name`, `collect_vscode_extensions`, `collect_cursor_extensions`, lines 495–728)
**Status:** issues_found

---

## Summary

The three new functions implement the algorithm specified in 02-RESEARCH.md accurately. NLS placeholder resolution via `.[$k]` (not `getpath`) is correct, the plutil dot-escaping is correct, `relativeLocation` is used exclusively for path construction (no naive id+version reconstruction), output is routed through `emit_item`/`flush_section`, and graceful degradation is present on all primary exit paths.

Three warnings were found: two are variants of the same root cause (missing `// ""` null-coalescing in `jq -r` field extractions in the file-fallback path, which can produce literal `"null"` strings in catalog output), and one is a missing plutil fallback for `relativeLocation` lookup in the CLI path. Two info items cover a missing `local` declaration for the loop variable `line` and code duplication between the two collectors.

No critical/blocking issues. The research verified that all real-world extensions have valid non-null `identifier.id`, `version`, and `relativeLocation` fields, so the null-coalescing omission is latent rather than immediately triggered — but it is a real correctness bug under abnormal input.

---

## Warnings

### WR-01: `jq -r` without `// ""` emits literal `"null"` string for absent/null fields in file-fallback path

**File:** `update-list.sh:614–616` (VS Code); `update-list.sh:704–706` (Cursor)

**Issue:** In the file-fallback jq path inside both collectors, all three field extractions use bare `jq -r '.<field>'` without a null-coalescing default:

```zsh
id=$(echo "$entry" | jq -r '.identifier.id' 2>/dev/null)
version=$(echo "$entry" | jq -r '.version' 2>/dev/null)
rel_loc=$(echo "$entry" | jq -r '.relativeLocation' 2>/dev/null)
```

When a field is absent or explicitly `null` in the JSON, `jq -r` emits the literal string `"null"` (not an empty string). This has three concrete consequences:

1. **`version` = `"null"`:** `emit_item` receives a non-empty version string `"null"`, producing catalog lines like `"Python (null) [ms-python.python]"`. The `// ""` guard in `emit_item` only skips empty strings, not the literal word `null`.

2. **`rel_loc` = `"null"`:** `pkg_json` is constructed as `"$ext_dir/null/package.json"`. The file does not exist, so `json_get` falls back gracefully (file guard at line 284), but `display_name` falls back to the extension ID instead of the real display name — a silent quality regression.

3. **`id` = `"null"`:** The `[[ -z "$id" ]] && continue` guard on line 617/707 does NOT catch the literal string `"null"` (non-empty). The entry is processed with `id="null"`, producing catalog lines like `"ExtName (1.0) [null]"`.

The research confirms all 69 real-machine extensions have valid non-null values for all three fields (02-RESEARCH.md, Flag 3 field analysis). The defect is latent under corrupt or future-schema inputs. It should still be fixed because the `// ""` idiom is trivially cheap and the failure mode (bogus catalog output) is non-obvious.

**Fix:** Add `// ""` null-coalescing to all three extractions in both collectors:

```zsh
# jq file-fallback path (lines 614–616 and 704–706)
id=$(echo "$entry" | jq -r '.identifier.id // ""' 2>/dev/null)
version=$(echo "$entry" | jq -r '.version // ""' 2>/dev/null)
rel_loc=$(echo "$entry" | jq -r '.relativeLocation // ""' 2>/dev/null)
```

Apply the same change in both `collect_vscode_extensions` and `collect_cursor_extensions`.

---

### WR-02: CLI path silently drops displayName resolution when jq is absent (no plutil fallback for `relativeLocation` lookup)

**File:** `update-list.sh:586–595` (VS Code CLI path); `update-list.sh:676–685` (Cursor CLI path)

**Issue:** When the editor CLI is present but jq is absent, the CLI path has no way to look up `relativeLocation` and silently falls back to raw extension IDs as display names for every extension:

```zsh
rel_loc=""
if [[ -f "$ext_json" ]] && command -v jq &>/dev/null; then
    rel_loc=$(jq -r --arg i "$id" \
        '.[] | select(.identifier.id == $i) | .relativeLocation' \
        "$ext_json" 2>/dev/null | head -1)
fi
if [[ -n "$rel_loc" ]]; then
    pkg_json="$ext_dir/$rel_loc/package.json"
    display_name=$(resolve_vsc_ext_name "$pkg_json" "$id")
else
    display_name="$id"   # ← always taken when jq absent
fi
```

The file-fallback path (lines 622–635) correctly has a full plutil index-loop that resolves `relativeLocation` without jq. The CLI path has no equivalent plutil branch — the omission is asymmetric. The result: on a machine where `code` or `cursor` is on PATH but jq is not installed, every extension is cataloged with its bare ID instead of a human-readable display name, with no warning printed. This contradicts the "graceful degradation with a warning" contract.

In practice, Homebrew installs both jq and VS Code/Cursor, making this combination unlikely. But it is a real code path that produces silently degraded output.

**Fix:** Add a plutil index-loop fallback for the `relativeLocation` lookup inside the CLI path, mirroring the file-fallback pattern. At minimum, emit a warning when jq is absent in the CLI path:

```zsh
rel_loc=""
if [[ -f "$ext_json" ]]; then
    if command -v jq &>/dev/null; then
        rel_loc=$(jq -r --arg i "$id" \
            '.[] | select(.identifier.id == $i) | .relativeLocation' \
            "$ext_json" 2>/dev/null | head -1)
    else
        # plutil fallback: scan by index for matching id
        local scan_idx=0
        while true; do
            local scan_id
            scan_id=$(plutil -extract "${scan_idx}.identifier.id" raw -o - "$ext_json" 2>/dev/null) || break
            if [[ "$scan_id" == "$id" ]]; then
                rel_loc=$(plutil -extract "${scan_idx}.relativeLocation" raw -o - "$ext_json" 2>/dev/null) || rel_loc=""
                break
            fi
            ((scan_idx++))
        done
    fi
fi
```

Apply the same fix in both `collect_vscode_extensions` (line ~586) and `collect_cursor_extensions` (line ~676).

---

### WR-03: `version` field — same `jq -r` null-string issue affects the CLI path's version split when extension ID itself contains no `@`

**File:** `update-list.sh:583` (VS Code); `update-list.sh:673` (Cursor)

**Issue:** This is a distinct failure mode from WR-01. In the CLI path:

```zsh
id="${line%@*}"
version="${line##*@}"
```

The split-on-last-`@` logic is correct and verified. However, if the CLI emits a line that contains no `@` character at all (e.g., a blank separator line slips through the `[[ -z "$line" ]] && continue` guard, or the CLI format changes), then:

- `id="${line%@*}"` — no `@` found, `%@*` matches nothing, `id = line` (the whole line)
- `version="${line##*@}"` — no `@` found, `##*@` matches nothing, `version = line` (also the whole line)

Result: `id` and `version` both equal the original unmodified line, and `emit_item` is called with duplicate values: `emit_item "line-content" "line-content" "line-content"`, producing a malformed catalog entry. The blank-line guard filters genuine blank lines, but non-blank malformed lines (e.g., `"Some warning: ..."` printed to stdout by the CLI) are not filtered.

VS Code's `code --list-extensions --show-versions` reliably outputs `id@version`, but the assumption is unguarded.

**Fix:** Add a guard after the split to skip lines that produced an empty version (which indicates the `@` was not found):

```zsh
id="${line%@*}"
version="${line##*@}"
# Guard: if no @ separator found, id and version are equal — skip malformed line
[[ "$id" == "$version" ]] && continue
```

---

## Info

### IN-01: Loop variable `line` not declared `local` in CLI path of both collectors

**File:** `update-list.sh:580` (VS Code); `update-list.sh:670` (Cursor)

**Issue:** The `while IFS= read -r line` loop variable `line` is used inside `collect_vscode_extensions` and `collect_cursor_extensions` but is not declared `local`. The project convention (CLAUDE.md) requires: "Use `local` for all function-scoped variables." The collector's other loop-scoped variables (`id`, `version`, `rel_loc`, `pkg_json`, `display_name`) are correctly declared local on line 569/659. The omission of `line` is inconsistent and leaks the loop variable into the global scope.

In Zsh, this does not cause a correctness bug in a single-threaded script (no concurrent reader), but it violates the stated convention and `line` could interfere with a caller or sibling function that also uses an undeclared `line` global.

**Fix:** Add `line` to the existing local declaration in both collectors:

```zsh
# update-list.sh line 569 (collect_vscode_extensions):
local id="" version="" rel_loc="" pkg_json="" display_name="" cli_output="" entry="" line=""

# update-list.sh line 659 (collect_cursor_extensions):
local id="" version="" rel_loc="" pkg_json="" display_name="" cli_output="" entry="" line=""
```

---

### IN-02: `collect_vscode_extensions` and `collect_cursor_extensions` are identical except for three literal substitutions — duplication creates a maintenance burden for Phase 3+ additions

**File:** `update-list.sh:566–638` vs `update-list.sh:656–728`

**Issue:** The two collector functions share ~95% of their code body. The only differences are:
- `ext_dir` value (`~/.vscode/extensions` vs `~/.cursor/extensions`)
- CLI command (`code` vs `cursor`)
- Section title string (`"VS Code Extensions"` vs `"Cursor Extensions"`)
- Warning/note message text

This is exactly the pattern the research document's "Don't Hand-Roll" table warned about for Phase 3/4: "Both collectors need it; inlining duplicates 15+ lines of fallback logic." The research recommended extracted helpers for NLS resolution (done — `resolve_vsc_ext_name`). The same principle applies here: a shared `_collect_vsc_compatible_extensions(ext_dir, cli_cmd, section_title)` helper would eliminate the 72-line duplication. When Phase 3 or Phase 4 adds another VS Code-compatible editor, the same logic must be copy-pasted a third time if not refactored now.

This is flagged as Info because the current duplication is correct and the refactoring would be purely structural. However, if any bug fix is applied to one collector (e.g., the WR-01, WR-02, WR-03 fixes above), the identical fix must be applied to the other collector — a known duplication tax.

**Fix:** Extract a shared inner function:

```zsh
# Shared implementation — called by both public collectors
_collect_vsc_compatible_extensions() {
    local ext_dir="$1"
    local cli_cmd="$2"
    local section_title="$3"
    # ... body of collect_vscode_extensions with ext_dir/cli_cmd/section_title substituted ...
}

collect_vscode_extensions() { _collect_vsc_compatible_extensions "$HOME/.vscode/extensions" "code" "VS Code Extensions"; }
collect_cursor_extensions()  { _collect_vsc_compatible_extensions "$HOME/.cursor/extensions" "cursor" "Cursor Extensions"; }
```

The refactoring is optional for Phase 2 correctness but is recommended before Phase 3/4 extends the pattern.

---

## Severity Summary

| ID | Severity | Title |
|----|----------|-------|
| WR-01 | WARNING | `jq -r` null-string for absent fields produces `"null"` in catalog output (file-fallback path) |
| WR-02 | WARNING | CLI path silently drops displayName resolution when jq absent (no plutil fallback for relativeLocation) |
| WR-03 | WARNING | CLI path: no-`@`-separator guard missing — malformed CLI output lines produce duplicate id/version |
| IN-01 | INFO | Loop variable `line` not declared `local` in CLI path of both collectors |
| IN-02 | INFO | ~72 lines duplicated between the two collectors; shared helper would reduce bug-fix surface |

---

_Reviewed: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
