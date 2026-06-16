---
phase: 10-computer-folder-identity-foundation
reviewed: 2026-06-14T15:25:51Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - update-list.sh
  - machine-labels.tsv
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-06-14T15:25:51Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the four Phase 10 commits (source-guard, validation rename, folder wiring, summary)
against the live `update-list.sh` and `machine-labels.tsv`. The three mechanical asks of the
phase are each implemented correctly and verified empirically:

- **Source-guard** — `[[ "$ZSH_EVAL_CONTEXT" =~ :file ]] && return 0` sits at line 2354, after
  the last function definition (`git_commit_and_push` ends at 2352) and before any main-block
  side effect (`display_usage` at 2361). Instrumented testing confirms `ZSH_EVAL_CONTEXT` is
  `toplevel:file` / `cmdarg:file` when sourced (guard fires, `return 0`) and `toplevel` when
  executed directly (guard is a no-op, execution falls through to main). Direct execution still
  reaches the banner; sourcing returns cleanly with all functions defined. No premature-return
  edge case found.
- **Validation rename** — `validate_machine_label`→`validate_computer_name` and the `_quiet`
  variant are renamed; the rule bodies are byte-for-byte equivalent (only the user-facing error
  noun changed from "label" to "computer name"). All allow/reject cases verified: rejects
  `/ [ ] tab newline` and leading/trailing whitespace; allows spaces, apostrophes, `-_.`. All
  three call sites updated (parse_arguments:226, resolve create-new:556, rename new-label:684);
  `grep` confirms zero stale `validate_machine_label` references anywhere.
- **Folder wiring** — `CURRENT_MACHINE="$TARGET_LOCATION"` (2390) feeds `OUTPUT_FILENAME` (2391).
  `get_target_location` (2375) runs before this point and exits fail-fast if unresolved, so
  `TARGET_LOCATION` is always set. `upsert_machine_label` writes `TARGET_LOCATION` as the TSV
  value, preserves comment/blank lines verbatim, and performs an atomic `.tmp`+`mv` (verified in
  fixture: no `.tmp` leftover, comments/blank/other-hosts preserved). Map header comment updated.
- **No regression** — hostname-first "keep current" menu (526), empty-Enter default (539-542),
  all four `while true` re-prompt loops (536, 553, 667, 681), and the pure-zsh `${base##*-}`
  timestamp parse (724-726) are all intact and unaltered.

`zsh -n` passes. No source files were modified during review.

The findings below concern a real semantic divergence introduced by the wiring change: the
machine-label resolution subsystem is now half-connected. `resolve_machine_label` still prompts
the user (and honors `--machine`) but its result is discarded, while the persisted/filename value
is silently overridden by `TARGET_LOCATION`. This is correctness-adjacent (no crash or data loss)
but produces user-surprising behavior, so the strongest items are Warnings.

## Warnings

### WR-01: `--machine` flag value and the interactive label menu are silently discarded

**File:** `update-list.sh:2390-2391` (consumers), `update-list.sh:439-570` (producer)
**Issue:** Phase 10 changed `CURRENT_MACHINE` from `$MACHINE_LABEL` to `$TARGET_LOCATION`, but
left the entire `resolve_machine_label` subsystem in place and still wired into the main block
(2381). The result: a user who runs `--machine "Kens Fancy Laptop"`, or who picks/creates a label
in the interactive menu, sees the script echo `Machine label: Kens Fancy Laptop` — yet the actual
catalog filename and the TSV value are both `personal` (the `TARGET_LOCATION`). Verified in
fixture: with `TARGET_LOCATION=personal` and `MACHINE_LABEL="Kens Fancy Laptop"`, the file written
is `MyHost<TAB>personal` and the filename uses `personal`. The supplied/chosen label has zero
effect. This violates the project's fail-fast / "make beliefs pay rent" conventions: an option
that prints a confirmation but does nothing is worse than an option that errors.

This is acknowledged as transitional ("prefer --computer in Phase 11", usage line 91), but as
shipped it is a live footgun: `--machine` is still advertised in `display_usage` (84, 91) and
still validated, so users will reasonably expect it to work.
**Fix:** Either (a) make `--machine` an explicit hard error for Phase 10 with a message pointing
at `--personal`/`--office`, or (b) suppress the misleading `Machine label: … (from --machine flag)`
/ `Machine label: …` confirmation lines and document clearly that the value is currently inert.
Preferred:
```zsh
# In parse_arguments, --machine case:
echo "ERROR: --machine is not wired in this version; the computer folder (personal/office) is the identity. Use --personal or --office."
exit 1
```

### WR-02: Non-interactive runs without a saved label abort even though the label is unused

**File:** `update-list.sh:469-473`
**Issue:** `resolve_machine_label` still runs in the main flow (2381) and still enforces its
non-interactive TTY guard: a brand-new host with no `--machine` flag and no saved-map entry will
`exit 1` with `"No machine label resolved and stdin is not a TTY"` when run from cron/CI — even
though the resolved label is now thrown away and `TARGET_LOCATION` (already known from
`--personal`/`--office`) is what actually drives the filename. A previously-working
`./update-list.sh --personal --no-commit </dev/null` cron job on a fresh machine now fails at the
label step for a value it never consumes. Verified in fixture: the guard fires and exits 1 on a
new host with `TARGET_LOCATION` already set.
**Fix:** Since the label no longer affects output, either skip `resolve_machine_label` entirely in
the main flow (let `upsert_machine_label` run standalone if the host→folder map is still wanted),
or short-circuit the function once `TARGET_LOCATION` is set:
```zsh
resolve_machine_label() {
    # Folder is identity in this phase; persist host->folder and return.
    if [[ -n "$TARGET_LOCATION" ]]; then
        upsert_machine_label
        return
    fi
    ...
}
```

### WR-03: `upsert_machine_label` data-line split is incompatible with the rename map-update split

**File:** `update-list.sh:400` vs `update-list.sh:776`
**Issue:** `upsert_machine_label` splits a data line with `local map_host="${line%%	*}"` using a
literal TAB inside the parameter expansion (line 400). `rename_machine`'s map rewriter uses the
explicit `$'\t'` form: `"${line%%$'\t'*}"` (778) and guards with `*$'\t'*` (776). The literal-TAB
form at 400 is correct today (the byte is a real TAB), but it is fragile: it is invisible in most
editors and a future reformat/whitespace-normalize pass can silently turn it into spaces, at which
point `map_host` would become the whole line and every host would be treated as non-matching —
appending a duplicate entry on every run instead of replacing. The two functions that parse the
same TSV format should use the same, explicit delimiter idiom.
**Fix:** Make line 400 use the explicit, reformat-proof form to match `rename_machine`:
```zsh
local map_host="${line%%$'\t'*}"
```

## Info

### IN-01: `MACHINE_LABEL` global and its config comment are now dead for the filename path

**File:** `update-list.sh:51`, `update-list.sh:441-568`
**Issue:** With `CURRENT_MACHINE` sourced from `TARGET_LOCATION`, the `MACHINE_LABEL` global is no
longer read by any output-producing code — it is set in `parse_arguments` (227) and throughout
`resolve_machine_label` (464, 562, 565) but the only former consumer (the old `CURRENT_MACHINE=`
line) was rewired away. The config-block comment at line 50-51 now reads "Computer folder for this
run's catalog filename (set by TARGET_LOCATION)" on the `MACHINE_LABEL=""` declaration, which is
self-contradictory: the variable is named `MACHINE_LABEL` but the comment describes `TARGET_LOCATION`.
**Fix:** Resolve alongside WR-01/WR-02. If the label subsystem is being deprecated, remove or
clearly comment the dead global; do not leave a `MACHINE_LABEL` declaration described as the
"computer folder … set by TARGET_LOCATION".

### IN-02: `--machine` usage text is internally inconsistent across the help banner

**File:** `update-list.sh:84` vs `update-list.sh:91`
**Issue:** The USAGE synopsis (84) still lists `--machine "Label"` as a normal option, while the
OPTIONS detail (91) reframes it as a "back-compat alias; prefer --computer in Phase 11". A reader
of the synopsis has no signal the flag is transitional/inert. Minor, but the two lines should tell
the same story.
**Fix:** Annotate the synopsis line or drop `--machine` from it until Phase 11 lands `--computer`.

### IN-03: `resolve_machine_label` comment header still claims it drives the filename

**File:** `update-list.sh:421-438`
**Issue:** The function doc still says it "Resolves the machine label for this run and sets
MACHINE_LABEL" with the resolution feeding the catalog filename — no longer true after the wiring
change. Stale documentation on a function whose output is now discarded will mislead the next
maintainer (directly contradicts the "map ≠ territory" principle in CLAUDE.md).
**Fix:** Update the header to state that the resolved value is currently only persisted to the
host→folder map (or remove the function per WR-02).

---

_Reviewed: 2026-06-14T15:25:51Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
