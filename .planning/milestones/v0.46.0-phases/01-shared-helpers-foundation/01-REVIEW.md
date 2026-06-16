---
phase: 01-shared-helpers-foundation
reviewed: 2026-06-13T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - update-list.sh
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: fixes_applied
---

# Phase 01: Code Review Report

**Reviewed:** 2026-06-13
**Depth:** standard (per-file analysis — focused on the 217-line insertion block, lines 259–474)
**Files Reviewed:** 1 (`update-list.sh`, new functions only)
**Status:** issues_found

## Summary

Four Zsh helper functions (`json_get`, `chrome_ext_name`, `emit_item`, `flush_section`) were inserted between `write_section` and `generate_catalog` as planned. The implementation is clean Zsh, passes `zsh -n` without error, uses `local`-scoped variables, `[[ ]]` conditionals, `command -v` probing, and proper quoting throughout. The plutil fallback chain is correct (no python3 stub risk).

One critical finding: `json_get` passes an unvalidated key to jq, and when the key is an empty string, jq's `getpath([] )` evaluates to the root object — causing the full JSON file contents to be echoed to stdout. This violates the FMT-03 "exactly one field" contract documented in the threat model and is a potential secret-disclosure vector for Phase 3 MCP config collectors. Three warnings cover an asymmetric defensive guard, a degenerate `__MSG___` edge case that is functionally safe but spec-incorrect, and a code quality concern with `local resolved` redeclaration. Two info items note minor style inconsistencies.

---

## Critical Issues

### CR-01: `json_get` with empty key echoes the entire JSON file (FMT-03 violation)

**File:** `update-list.sh:286–297`

**Issue:** `json_get` validates that the file exists but does not validate that the key is non-empty. When `jq` is present and an empty string is passed as the key argument, the expression `getpath($k | split("."))` evaluates as `getpath([])` — `split(".")` on `""` returns `[]` in jq, and `getpath([])` returns the root object. The full JSON object is then printed to stdout by `echo "$value"`. This means a caller that accidentally passes an empty variable as the key (e.g. from an unset `$field` in a Phase 3 collector) will receive the entire JSON blob on stdout rather than an empty string.

The Phase 1 threat model (T-01-02) explicitly states: "json_get extracts exactly one field by key path and echoes it to stdout. It does not enumerate sibling keys, log the full file, or write to OUTPUT_FILE." An empty key breaks this structural guarantee. Phase 3 MCP collectors will read config files that may contain `env`, `headers`, or API key fields — exactly the secrets the threat model is protecting against.

Verification (live test):
```
$ echo '{"name":"test","api_key":"secret"}' > /tmp/t.json
$ jq -r --arg k "" 'getpath($k | split(".")) // ""' /tmp/t.json
{
  "name": "test",
  "api_key": "secret"
}
```

The `plutil` branch is not affected (plutil exits 1 on empty key lookup, `|| value=""` produces empty string correctly).

**Fix:** Add a key non-empty guard immediately after the file guard, before the jq/plutil branch:

```zsh
json_get() {
    local file="$1"
    local key="$2"
    local value=""

    # Guard: file must exist and be readable
    [[ -f "$file" ]] || { echo ""; return; }
    # Guard: key must be non-empty (empty key causes jq to dump entire root object)
    [[ -n "$key" ]] || { echo ""; return; }

    if command -v jq &>/dev/null; then
        value=$(jq -r --arg k "$key" 'getpath($k | split(".")) // ""' "$file" 2>/dev/null)
    else
        value=$(plutil -extract "$key" raw -o - "$file" 2>/dev/null) || value=""
    fi

    echo "$value"
}
```

---

## Warnings

### WR-01: jq branch in `json_get` lacks the `|| value=""` defensive guard present in the plutil branch

**File:** `update-list.sh:289` (jq branch) vs `update-list.sh:294` (plutil branch)

**Issue:** The plutil branch defensively resets `value` on non-zero exit:
```zsh
value=$(plutil -extract "$key" raw -o - "$file" 2>/dev/null) || value=""
```
The jq branch has no equivalent guard:
```zsh
value=$(jq -r --arg k "$key" 'getpath($k | split(".")) // ""' "$file" 2>/dev/null)
```

In the current script (no `set -e`) this is functionally harmless: a failing jq produces empty stdout, `value` is set to `""`, and `echo "$value"` returns correctly. However the two branches are documented in RESEARCH as peers with the same "returns empty on error" contract, and they should be coded defensively to the same standard. If a future maintainer adds `set -o errexit` to the script, the jq branch would abort on a malformed JSON file (jq exits 5 on parse error) while the plutil branch would silently continue — a behavioral asymmetry that would be hard to diagnose.

**Fix:**
```zsh
value=$(jq -r --arg k "$key" 'getpath($k | split(".")) // ""' "$file" 2>/dev/null) || value=""
```

---

### WR-02: `__MSG___` (zero-length key between prefix and suffix) is mis-classified as a message placeholder

**File:** `update-list.sh:339`

**Issue:** The pattern check `[[ "$name" != __MSG_*__ ]]` uses Zsh glob matching where `*` matches zero or more characters. This means the degenerate string `"__MSG___"` (prefix `__MSG_`, empty key, suffix `__`) matches the MSG branch rather than being treated as a plain literal name. The Chrome extension spec requires the key portion to be non-empty (`__MSG_<messageName>__` where `<messageName>` is a valid identifier).

After stripping the prefix and suffix, `msg_key` becomes `""`. In the jq branch, `to_entries[] | select(.key | ascii_downcase == "")` looks for keys with an empty string name — messages.json files do not have such keys in practice, so the function falls through to `echo "$ext_id"` and the output is correct. However, the function is advertised as "never emits a blank name or a raw `__MSG_` string" — with `__MSG___`, the name in the manifest is not a raw placeholder in the usual sense, and it would more naturally be treated as a plain (if unusual) name rather than triggering locale resolution.

More concretely: if a real extension name happened to be the literal string `"__MSG___"` (unlikely but malformed), the current code discards that string and emits the extension ID instead. The user would get the ID rather than the literal name, which is an incorrect result given the intent.

**Fix:** Require at least one character between the prefix and suffix:
```zsh
if [[ "$name" != __MSG_?*__ ]]; then
```
`?*` requires one character followed by zero or more — this excludes `__MSG___` from the placeholder branch and lets it pass through as a plain name.

---

### WR-03: `local resolved` is declared twice in `chrome_ext_name` (redundant re-declaration in same function scope)

**File:** `update-list.sh:365` and `update-list.sh:375`

**Issue:** In Zsh, `local` is function-scoped, not block-scoped. Both declarations — one in the `if` branch (line 365) and one in the `else` branch (line 375) — refer to the same variable `resolved` in the same function scope. Since only one branch executes at runtime this produces no behavioral bug, but the double declaration is misleading: it suggests the two branches have independent `resolved` variables, which they do not. A reader maintaining this function may introduce the variable in a new branch thinking the prior declarations do not apply, leading to accidental reuse of a stale value.

**Fix:** Declare `local resolved=""` once at the top of the function alongside the other local declarations:

```zsh
chrome_ext_name() {
    local manifest="$1"
    local name=""
    local locale=""
    local msg_key=""
    local messages_file=""
    local ext_id=""
    local resolved=""   # ← add here, remove from both branches below
    ...
}
```

---

## Info

### IN-01: `flush_section` uses `echo` for the empty-section path and `printf` for the normal path — minor inconsistency

**File:** `update-list.sh:469` and `update-list.sh:471`

**Issue:**
```zsh
echo "  (none found)" >> "$OUTPUT_FILE"   # empty-section path
printf "%s\n" "${_section_lines[@]}" | LC_ALL=C sort -f -u >> "$OUTPUT_FILE"   # normal path
```

Both produce equivalent output for the stated purpose. However using `printf` throughout would be more consistent with the convention used for the data path, and avoids any theoretical issues with `echo` interpreting escape sequences on unusual platforms (Zsh's `echo` does not interpret backslash escapes by default, so this is not a real risk here). The inconsistency is purely cosmetic but may cause confusion in a function that is otherwise precise about output format.

**Fix:** Replace the `echo` with `printf`:
```zsh
printf "  (none found)\n" >> "$OUTPUT_FILE"
```

---

### IN-02: Redundant `command -v jq` probe inside `chrome_ext_name` — jq availability is already checked by the `json_get` calls

**File:** `update-list.sh:364`

**Issue:** `chrome_ext_name` calls `json_get` twice (lines 336 and 350), each of which internally probes `command -v jq`. Then on line 364, `chrome_ext_name` issues a third independent `command -v jq` probe for the messages.json lookup. All three probes will return the same result within a single script invocation (the PATH does not change mid-run), so the redundancy has no behavioral effect. However, it adds cognitive overhead: a reader must understand that the function's internal jq/plutil branching is independent from `json_get`'s internal branching, which is not immediately obvious.

A cached variable (e.g. `_HAS_JQ`) set once at script initialization would eliminate repeated probes across all four helpers and all collectors in Phases 2–4. This is a design-level concern worth addressing before the Phase 2 collectors are written, not a bug in the current code.

**Fix (optional, Phase 2 pre-work):** Add to the script-level configuration block (after line 48):
```zsh
# Cache jq availability once at startup (avoid repeated command -v jq throughout)
command -v jq &>/dev/null && _HAS_JQ=1 || _HAS_JQ=0
```
Then replace all `if command -v jq &>/dev/null; then` checks with `if [[ $_HAS_JQ -eq 1 ]]; then`.

---

## Finding Summary by Severity

| ID | Severity | Function | Issue |
|----|----------|----------|-------|
| CR-01 | BLOCKER | `json_get` | Empty key causes full JSON file to be dumped to stdout; violates FMT-03 single-field contract; secret-disclosure risk for Phase 3 MCP collectors |
| WR-01 | WARNING | `json_get` | jq branch lacks `|| value=""` guard present in plutil branch; asymmetric defensive coding |
| WR-02 | WARNING | `chrome_ext_name` | `__MSG___` (zero-length key) incorrectly classified as MSG placeholder due to `*` matching zero chars; `?*` would be correct |
| WR-03 | WARNING | `chrome_ext_name` | `local resolved` declared twice in same function scope; misleading to maintainers |
| IN-01 | INFO | `flush_section` | `echo` vs `printf` inconsistency between empty and normal paths |
| IN-02 | INFO | `chrome_ext_name` | Redundant `command -v jq` probe; worth caching at script-init before Phase 2 adds more callers |

---

_Reviewed: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
