---
status: partial
phase: 10-computer-folder-identity-foundation
review: 10-REVIEW.md
findings_in_scope: 3
fixed: 1
deferred: 5
---

# Phase 10 Code Review — Fix Disposition

## Fixed

- **WR-03** (`995a725`): `upsert_machine_label`'s data-line TAB split now uses the explicit
  `${line%%$'\t'*}` form, matching `rename_machine`'s split (line 778). Removes the
  reformat-fragile literal embedded TAB. `zsh -n` passes; both split sites consistent.

## Deferred to Phase 11 (Computer Selection & CLI) — by design

These findings are artifacts of the deliberate phase boundary: Phase 10 lays the
folder-identity foundation; Phase 11 replaces `resolve_machine_label` with `select_computer`
and turns `--machine` into a `--computer` alias. Fixing them in Phase 10 would pre-implement
Phase 11 and be overwritten next phase.

- **WR-01** — `--machine` flag and the interactive label menu are accepted but ignored
  (filename/TSV use the folder). Resolved in Phase 11: `--machine` becomes a back-compat
  alias for `--computer`, and the label menu is replaced by the computer menu.
- **WR-02** — non-interactive fresh-host runs `exit 1` at the label TTY guard (the guard
  pre-existed from v0.48.0; it now blocks for a value that's ignored). Resolved in Phase 11
  when `select_computer` replaces `resolve_machine_label` and its guard logic.
- **IN-01** — the now-dead `MACHINE_LABEL` global + self-contradictory comment. Removed in
  Phase 11 when the label path is replaced.
- **IN-02** — `--machine` help text inconsistency. Updated in Phase 11 (display_usage rewrite
  for `--computer`/aliases).
- **IN-03** — stale `resolve_machine_label` doc header. Removed/replaced in Phase 11.

## Verification

All checks non-destructive (no live `./update-list.sh` run). The Phase 11 plan/CONTEXT must
explicitly carry WR-01, WR-02, IN-01, IN-02, IN-03 as required cleanup so they are not lost.
