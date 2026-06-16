---
phase: 04-browser-collectors
reviewed: 2026-06-13T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - update-list.sh
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: fixed
---

# Phase 4: Browser Collectors — Code Review

**Reviewed:** 2026-06-13
**Depth:** standard
**Files Reviewed:** 1 (`update-list.sh` — `collect_chrome_extensions` lines 1253–1311 and `collect_firefox_extensions` lines 1328–1380)
**Status:** issues_found

---

## Summary

Phase 4 adds two well-structured Zsh collector functions. The established Phase 1–3 patterns are faithfully replicated: `setopt local_options null_glob` at function top, `_section_lines=()` defensive reset, null-glob guards on every glob loop, all paths double-quoted, `emit_item` → `flush_section` pipeline, `flush_section` called once after the outer loop for correct cross-profile dedup.

No critical bugs, security vulnerabilities, or data-loss risks were found. Two warnings were found — one correctness issue in the Firefox profile parser and one silent-skip risk in the Chrome version-selector — plus two minor info items.

---

## Warnings

### WR-01: Firefox `profiles.ini` CRLF not stripped — all profiles silently skipped on CR-contaminated ini files

**File:** `update-list.sh:1376`

**Issue:** The pipeline that extracts `Path=` values from `profiles.ini` is:

```zsh
done < <(grep '^Path=' "$profiles_ini" 2>/dev/null | sed 's/^Path=//')
```

`sed 's/^Path=//'` strips the key prefix but leaves any trailing `\r` intact. Firefox on macOS writes `profiles.ini` with Unix LF line endings, so this is normally harmless. However, if the file is ever created or edited on Windows — or synced through a cloud service that normalises line endings — every extracted `rel_path` will carry a trailing carriage-return byte. The path constructed from it:

```zsh
ext_json="${ff_dir}/${rel_path}/extensions.json"
# expands to: .../Firefox/Profiles/rv4siqj3.default-release\r/extensions.json
```

`[[ -f "$ext_json" ]]` evaluates `false` for every profile, `continue` skips them all, and `flush_section` writes `(none found)` with no diagnostic. The script exits successfully, but the Firefox section is silently empty.

**Fix:** Add `tr -d '\r'` to the extraction pipeline:

```zsh
done < <(grep '^Path=' "$profiles_ini" 2>/dev/null | sed 's/^Path=//' | tr -d '\r')
```

---

### WR-02: Chrome `ls -1` for version-dir selection includes non-version entries — valid extension silently skipped

**File:** `update-list.sh:1296`

**Issue:**

```zsh
ver_dir=$(ls -1 "$ext_dir" 2>/dev/null | sort -V | tail -1)
```

`ls -1` lists *all* entries (files and directories) inside the extension-ID directory. Chrome normally stores only versioned subdirectories (`N.N.N_N`) there, but it also writes other entries in practice. Specifically:

- The `_metadata` directory exists at `Default/Extensions/_metadata/` (at the `Extensions/` level, not per-ID level), but Chrome also stores per-ID metadata in files such as `_crx_invalidation_map` inside some extension-ID directories.
- If any such non-version entry sorts *higher* than the real version dirs under `sort -V` (which is possible for entries starting with `_` on macOS BSD sort's version-sort algorithm), `tail -1` selects it as `ver_dir`.
- `manifest="${ext_dir}${ver_dir}/manifest.json"` is then a non-existent path; `[[ -f "$manifest" ]] || continue` silently skips the extension.
- The user extension is absent from the catalog with no diagnostic.

The existing `[[ -f "$manifest" ]] || continue` guard prevents wrong data from being emitted, but it also silently drops a valid extension.

**Fix:** Restrict `ls -1` to directory entries that start with a digit (Chrome version dirs always start with a digit):

```zsh
ver_dir=$(ls -1d "$ext_dir"[0-9]*/ 2>/dev/null | xargs -I{} basename {} | sort -V | tail -1)
```

Or more portably without xargs, filter through `grep`:

```zsh
ver_dir=$(ls -1 "$ext_dir" 2>/dev/null | grep -E '^[0-9]' | sort -V | tail -1)
```

Either approach limits candidates to version-like entries, making it impossible for a non-version file or directory to be selected.

---

## Info

### IN-01: Firefox jq path emits literal `"null"` if both `.defaultLocale.name` and `.id` are null

**File:** `update-list.sh:1355–1357`

**Issue:** The jq expression:

```
"\(.defaultLocale.name // .id)\t\(.version // "")\t\(.id)"
```

The `//` alternative returns the right operand if the left is `false` or `null`. If an addon has no `defaultLocale.name` *and* no `id` (a malformed entry in `extensions.json`), jq outputs the literal string `"null"` for both the name field and the `.id` field. The `-r` flag renders `null` as the four-character string `"null"`. The `[[ -z "$id" ]] && continue` guard on line 1352 does not catch this because `"null"` is non-empty, so `emit_item "null" "" "null"` executes, writing `"null [null]"` to the catalog.

In practice, every entry in a valid `extensions.json` has a non-null `.id` — this is Firefox's own generated file. The bug would only trigger on corruption.

**Fix (optional hardening):** Add an explicit null guard in the jq expression:

```
"\(.defaultLocale.name // .id // "")\t\(.version // "")\t\(.id // "")"
```

And change the Zsh guard to check for the literal string "null":

```zsh
[[ -z "$id" || "$id" == "null" ]] && continue
```

---

### IN-02: Chrome profile enumeration iterates `_metadata` directory as an extension ID (harmless no-op)

**File:** `update-list.sh:1271–1307`

**Issue:** Chrome maintains a `Default/Extensions/_metadata/` directory at the `Extensions/` level. The glob `"${profile_dir}/Extensions"/*/` picks it up. `ext_id=$(basename "$ext_dir")` evaluates to `"_metadata"`. The 10-ID component denylist does not match `"_metadata"`, and neither does the `Temp` guard. The iteration proceeds:

1. `ls -1 "$ext_dir"` lists `_metadata`'s contents (Chrome internal metadata files, not version dirs).
2. `sort -V | tail -1` picks one filename.
3. `manifest="${ext_dir}${ver_dir}/manifest.json"` is a nonexistent path.
4. `[[ -f "$manifest" ]] || continue` — correctly skips.

No wrong data is emitted. The no-op costs one extra `ls`, one `sort`, and one `[[ -f ]]` check per run. This is harmless but means one unnecessary iteration always runs on any Chrome installation.

**Fix (optional):** Add a guard to skip entries that start with `_` (Chrome's internal directories are consistently prefixed with underscore):

```zsh
[[ "$ext_id" == _* ]] && continue
```

Place this immediately after the `Temp` guard at line 1277.

---

## Structural Findings (fallow)

No structural pre-pass was provided for this review.

---

## Severity Summary

| ID | Severity | Function | Description |
|----|----------|----------|-------------|
| WR-01 | WARNING | `collect_firefox_extensions` | CRLF in `profiles.ini` silently empties Firefox section |
| WR-02 | WARNING | `collect_chrome_extensions` | `ls -1` picks non-version entries; valid extension silently skipped |
| IN-01 | INFO | `collect_firefox_extensions` | jq emits literal `"null"` if `.id` is null in malformed JSON |
| IN-02 | INFO | `collect_chrome_extensions` | `_metadata` dir iterates as a no-op extension ID |

**Critical: 0 | Warning: 2 | Info: 2 | Total: 4**

---

_Reviewed: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
