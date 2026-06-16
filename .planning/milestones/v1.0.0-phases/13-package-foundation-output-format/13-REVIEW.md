---
phase: 13-package-foundation-output-format
reviewed: 2026-06-14T20:34:06Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/maccat/helpers/chrome_name.py
  - src/maccat/helpers/vsc_name.py
findings:
  critical: 0
  warning: 0
  info: 1
  total: 1
status: clean
---

# Phase 13: Code Review Report

**Reviewed:** 2026-06-14T20:34:06Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** clean

## Summary

Final re-review (iteration 3, the cap) of the two extension-name resolution
helpers. I verified the two prior warnings (WR-01, WR-02) are fixed and that the
fixes introduced no regressions, tracing both helpers against the zsh reference
`update-list.sh` (json_get lines 1099–1145, chrome_ext_name 1148–1214,
resolve_vsc_ext_name 1316–1367).

**Both iteration-2 fixes confirmed correct:**

1. **chrome_name.py — keep the FIRST case-insensitive match (`head -1` parity).**
   The zsh path is
   `jq 'to_entries[] | select(.key|ascii_downcase==$k) | .value.message' | head -1`.
   The Python now iterates `messages.items()` (line 69) in insertion order
   (== JSON input order == jq `to_entries` order; preserved by `json.loads` on
   Python 3.7+) and returns at the first case-insensitive key match. Crucially,
   when the first match is unusable — value not a dict, or `message`
   absent/empty/non-string — it returns `ext_id` (line 75) instead of continuing
   to a later colliding key. This exactly mirrors `head -1` capturing the first
   output line (including an empty `jq -r null` line) followed by the
   `[[ -n "$resolved" ]]` test failing and falling through to `ext_id`. A
   later-match-wins implementation (the old dict-comprehension) would have
   diverged; the new loop does not. Verified.

2. **chrome_name.py / vsc_name.py — non-string resolved value degrades to `ext_id`.**
   Chrome: a dict match whose `.message` is non-string returns `ext_id`
   (lines 71–75). VS Code NLS: a non-string `nls.get(nls_key)` — e.g. the NLS v2
   `{"message": ..., "comment": [...]}` object form — returns `ext_id`
   (lines 66–68). This is the intended, correct graceful-degradation behavior:
   `str(dict)` / `str(int)` can never reproduce jq's JSON serialization
   byte-for-byte, and a flat non-empty string is the only usable display name, so
   degrading to `ext_id` is the only non-corrupting choice. Per the phase parity
   constraints this is correct and is explicitly NOT flagged.

**No crashes, no happy-path byte divergence, no regressions.**
- `isinstance(messages, dict)` (line 52) and `isinstance(nls, dict)` (line 53)
  correctly prevent `AttributeError` aborts on valid-JSON-but-not-object inputs,
  matching the zsh `2>/dev/null` degradation to `ext_id`.
- The exception tuples `(json.JSONDecodeError, OSError, UnicodeDecodeError)`
  cover parse, IO, and decode failures; nothing escapes to abort the catalog run.
- VS Code `%key%` placeholder boundary parity verified empirically against the
  zsh `%?*%` glob: `%%`→plain, `%x%`→NLS, `%`→plain — identical in both. The
  `len(dn) > 2` guard is exactly right because the single-char `%` delimiters do
  not overlap the `?*`.
- Empty / missing `name` and `displayName` correctly fall back to `ext_id`.
- VS Code flat-key `.get(nls_key)` (not `json_get` dotted traversal) correctly
  handles literal-dot keys like `extension.title`.

One sub-boundary observation on the Chrome `__MSG_..__` length guard is recorded
as Info below. It affects only a malformed, non-spec `name` value, never a real
Chrome manifest, never the happy path, and predates these fixes (not a
regression). It does not block, so the status remains `clean`.

## Narrative Findings (AI reviewer)

## Info

### IN-01: Chrome `__MSG_` placeholder length guard is off-by-one vs the zsh `__MSG_?*__` glob (malformed-input only)

**File:** `src/maccat/helpers/chrome_name.py:30`
**Issue:**
The guard uses `len(name) > len("__MSG__")`, i.e. `len(name) > 7`, so the 8-char
value `"__MSG___"` (empty message key) is classified as a placeholder. The zsh
glob `[[ "$name" != __MSG_?*__ ]]` requires the `?*` (≥1 char) to not overlap the
2-char `__` suffix, so its minimum match length is 9 (`__MSG_X__`). `"__MSG___"`
(8 chars) does NOT match the zsh glob and is therefore treated as a plain name.
Verified empirically in both runtimes:

- zsh: `"__MSG___"` → PLAIN → echoes the literal `__MSG___`.
- Python: `"__MSG___"` → placeholder with empty key → NLS lookup fails →
  returns `ext_id`.

This is a deterministic divergence, but only for `"__MSG___"`, which is not a
valid Chrome name (the `__MSG_<key>__` spec requires a non-empty key) and will
not appear in any real `manifest.json`. There is no crash, no happy-path impact,
and the guard predates the iteration-2 fixes (not a regression). Recorded for
completeness only; does not affect the `clean` status.

**Fix (optional exact-parity hardening):** compare against `8`, so the zsh glob's
minimum match length is reproduced and the empty-key 8-char string is treated as
a plain name:

```python
if not (
    name.startswith("__MSG_")
    and name.endswith("__")
    and len(name) > 8  # zsh __MSG_?*__ glob min match is 9 chars (__MSG_X__)
):
    return name if name else ext_id
```

---

_Reviewed: 2026-06-14T20:34:06Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
