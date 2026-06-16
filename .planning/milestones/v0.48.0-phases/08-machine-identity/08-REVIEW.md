---
phase: 08-machine-identity
reviewed: 2026-06-14T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - update-list.sh
  - machine-labels.tsv
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 8: Code Review Report (Iteration 2 — Fix Verification)

**Reviewed:** 2026-06-14
**Depth:** standard
**Files Reviewed:** 2
**Status:** clean

## Summary

This is iteration 2 of the auto fix→review loop. The prior pass reported 1 BLOCKER
(CR-01: broken label-validation regex) and 4 warnings (WR-01 interior TAB/newline;
WR-02 read loops dropping final newline-less line; WR-03 `--machine` swallowing the
next flag; WR-04 `--no-commit` instruction). I verified every one of these against the
current source via reading, `zsh -n`, and isolated regex/loop reproductions. The script
was NOT run end-to-end (destructive per instructions).

**Result: all five prior findings are genuinely resolved, and no regressions were
introduced by the fixes.** Only two minor INFO items remain — neither is a defect.

### Verification detail

**CR-01 (validation regex) — RESOLVED.** `validate_machine_label` (line 125) now uses
`[[ "$val" =~ '[][/]' ]]`. Reproduced against the required cases:

| Input | Result |
|-------|--------|
| `Example Computer` | ALLOW (spaces + apostrophe) |
| `has/slash` | REJECT |
| `has[bracket` | REJECT |
| `has]bracket` | REJECT |
| `has[both]` | REJECT |
| `with-dash_and.dot` | ALLOW |

The bracket expression `[][/]` correctly denotes the literal set `{ ] , [ , / }` (the `]`
placed first is treated as a literal member), and single-quoting prevents zsh globbing.
Confirmed the regex matches the documented intent and over-rejects nothing.

**WR-01 (interior TAB/newline) — RESOLVED.** Lines 132–135 add
`[[ "$val" == *$'\t'* || "$val" == *$'\n'* ]]`. Reproduced: a tab-containing label and a
newline-containing label are both rejected; a clean label with spaces passes. This protects
the TSV column delimiter and prevents one logical entry spanning multiple physical lines.

**WR-02 (final newline-less line dropped) — RESOLVED.** Both the upsert rewrite loop
(line 336) and the two map-read loops (lines 401, 427) now use
`... read -r ... || [[ -n "$var" ]]`. Reproduced against a TSV file with **no** trailing
newline: the final `host2\tKeep Me` entry is read correctly in all three loop shapes, and
the upsert round-trip both preserves it and writes it back with a trailing newline.

**WR-03 (`--machine` swallows next flag) — RESOLVED.** Line 181 guard is
`[[ -z "$2" || "$2" == --* ]]`. Reproduced: `--machine --no-commit`, `--machine --office`,
`--machine` (no value), and `--machine --weird` all error with
"ERROR: --machine requires a value"; `--machine "My Mac"` accepts the label. Correct.

**WR-04 (`--no-commit` instruction) — RESOLVED.** Usage text (lines 79, 84) documents
`--no-commit` accurately as "Skip automatic git commit and push," and the `parse_arguments`
case (line 162) sets `AUTO_COMMIT=false`. Consistent.

### Regression checks (all clear)

- **Flag → map → menu precedence** intact: `resolve_machine_label` exits early on the
  flag path (line 389), then the saved-map path (line 411), then the TTY guard (line 418),
  then the interactive menu. Main block calls it after `parse_arguments` (line 2004) so the
  flag value is honored.
- **Upsert atomic write** intact: `:> "$tmp_file"` then `mv "$tmp_file" "$map_file"`
  (line 364). Round-trip reproduction preserved comment lines, blank lines, other hosts,
  and a legacy no-TAB single-column line verbatim while correctly replacing the target host.
- **`retain_newest_per_host` `[label]` parsing** intact: `${tmp%\]-*}` correctly extracts
  hosts containing spaces, dots, and apostrophes from filenames of the form
  `mac-software-list-[Example Computer]-20260614120000.txt`. Because the validator forbids
  `]`, `/`, tab, and newline in labels, no valid label can break this split or the filename.
- **`--archive-days` validation** unaffected: short-circuit `[[ =~ ^[0-9]+$ ]] && (( val >= 1 ))`
  rejects `0`, `-5`, `1.5`, `abc`, and empty; accepts `30` and `007`.
- **`zsh -n update-list.sh`** passes — single-quoted regex, new guards, and loop changes
  all parse correctly.
- **Empty-array menu loop** safe: dedup `for existing in "${labels[@]}"` is a no-op when no
  labels exist; create-new index math (`#labels + 1`) is correct and `labels[$choice]` is
  only indexed for valid `1..#labels`.

## Info

### IN-01: `--machine=Label` form is silently unsupported

**File:** `update-list.sh:180-189`
**Issue:** Only the space-separated form `--machine "Label"` is handled. Passing
`--machine=My Mac` falls through to the `*)` case and errors as "Invalid option
'--machine=My Mac'". This matches the documented usage (line 86 shows `--machine "Label"`),
so it is not a defect — but the error message names the whole token rather than hinting at
the supported form, which could confuse a user who tried the `=` form.
**Fix:** Optional. If desired, add a `--machine=*` branch that strips the prefix and
validates, e.g. `--machine=*) val="${1#--machine=}"; validate_machine_label "$val"; ...`.
Otherwise leave as-is; current behavior is safe and documented.

### IN-02: Menu "select existing" path does not re-validate the stored label

**File:** `update-list.sh:474`
**Issue:** When the user picks an existing label from the interactive menu,
`MACHINE_LABEL="${labels[$choice]}"` is assigned without calling `validate_machine_label`.
This is acceptable because every label is validated before it can be written to the map
(flag path line 186, create-new path line 470), so stored labels are already clean. The only
way an invalid label could reach the map is a hand-edited TSV file — an out-of-band action.
**Fix:** Optional defense-in-depth: call `validate_machine_label "${labels[$choice]}"` after
selection, or validate each label while building the `labels` array so a corrupted hand-edit
is caught rather than propagated into a filename. Not required for this phase.

---

_Reviewed: 2026-06-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
