---
phase: 11-computer-selection-cli
plan: "01"
subsystem: cli-selection
tags: [zsh, interactive-menu, computer-folder, machine-labels]
requires:
  - "validate_computer_name_quiet (Phase 10)"
  - "upsert_machine_label (Phase 10)"
  - "machine-labels.tsv hostname->folder map (Phase 10)"
provides:
  - "select_computer function (always-shown computer-folder menu)"
affects:
  - "update-list.sh main block (rewire deferred to Plan 02)"
tech-stack:
  added: []
  patterns:
    - "Dynamic folder discovery via zsh dirs-only null-glob qualifier *(/N)"
    - "Remembered-first then alphabetical ordering via (@o) array sort + promote"
    - "EOF-as-Quit on read; case-insensitive q/quit via ${choice:l}"
key-files:
  created: []
  modified:
    - "update-list.sh (added select_computer above the source-guard)"
decisions:
  - "select_computer always shows the menu; a saved map entry only marks the Enter-default (never fast-exits) per CONTEXT Area 2"
  - "Discovery is fully dynamic (union of catalog-bearing top-level dirs + map values); no hardcoded personal/office and no denylist — infra dirs excluded naturally"
  - "Flag path is select-or-create (mkdir -p) and upserts the map, unlike the legacy label analog"
metrics:
  duration: ~6 min
  completed: 2026-06-14
  tasks: 2
  files: 1
---

# Phase 11 Plan 01: select_computer Function Summary

Added a single always-shown `select_computer` Zsh function to `update-list.sh` that
discovers existing computer folders dynamically, marks this Mac's remembered folder as
the Enter-default, and handles Create-new / Quit (number / q / quit / EOF) — implementing
SEL-01..04 and the selection half of QUIT-01.

## What Was Built

- **`select_computer()`** defined immediately above `get_target_location` (and well above
  the source-guard at line 2354, so it remains sourceable for isolated tests).
  - **Flag short-circuit:** when `TARGET_LOCATION` is preset by a flag, `mkdir -p`s the
    folder (select-or-create), calls `upsert_machine_label`, echoes
    `Computer: <name> (from command-line argument)`, returns.
  - **Map lookup:** reads `machine-labels.tsv` for this hostname's remembered folder into
    `saved_folder` without fast-exiting (menu is always shown). Absent row ⇒ no default.
  - **TTY guard:** non-interactive with no flag fails fast:
    `ERROR: No computer selected and stdin is not a TTY. Pass --computer "Name".` (exit 1).
  - **Discovery:** union of (a) top-level dirs containing `mac-software-list-*.txt`
    (dirs-only null-glob `*(/N)`) and (b) `machine-labels.tsv` values, deduped via a local
    `_name_in_list` helper, sorted lexically with `(@o)`, then the remembered folder
    promoted to index 1.
  - **Menu:** 1-indexed list; remembered row suffixed with the exact em-dash marker
    `(this machine — default)`; `Create new computer` and `Quit` appended.
  - **Input loop:** Enter-default only when `saved_folder` is set; `q`/`quit`
    (case-insensitive via `${choice:l}`) and EOF (`if ! read -r choice`) map to Quit;
    out-of-range / non-numeric / empty-without-default re-prompt indefinitely.
  - **Branches:** Quit prints `No catalog written.` and `exit 0`; Create-new re-prompts
    via `validate_computer_name_quiet` then `mkdir -p`s; Select sets `TARGET_LOCATION` from
    the 1-indexed array. Every non-Quit selection calls `upsert_machine_label`.

This plan ONLY adds the function. Legacy `get_target_location` and `resolve_machine_label`
remain in place and untouched; the main block still runs the old path until Plan 02 rewires it.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | select_computer skeleton (flag short-circuit, map lookup, TTY guard, discovery) | `d1cf891` | update-list.sh |
| 2 | Complete menu, input loop, Quit/Create-new/Select branches | `89e6e68` | update-list.sh |

## Verification

Per the project's destructive-script constraint, `update-list.sh` was NEVER run live.

**Syntax / source assertions (mandatory floor — all pass):**
- `zsh -n update-list.sh` exits 0 after each task.
- `grep -c 'select_computer()'` == 1; definition precedes the source-guard (awk check passes).
- `*(/N)` present (dirs-only glob); `(@o)computers` present (lexical sort).
- TTY-guard text, `(this machine — default)` em-dash marker, `No catalog written.`,
  `or Enter for the default`, `Create new computer`, `${choice:l}`, and `quit_idx` (9×) all present.
- Note: a few acceptance-criteria greps written as basic-regex patterns containing `${...}`
  (e.g. `'"${choice:l}"'`, `'mkdir -p "${SCRIPT_DIR}/${TARGET_LOCATION}"'`) return 0 under BRE
  brace-interval interpretation; the equivalent `grep -F` fixed-string checks confirm the lines
  are present (>= 1). This is a grep-flavor artifact, not a missing-code defect.

**Isolated behavioral tests (best-effort — all pass):**
Built a `mktemp -d` fixture (`alpha/`, `office/` with catalogs; `.git/`, `docs/` without;
`machine-labels.tsv` mapping `$(hostname) -> office`), sourced the script with `SCRIPT_DIR`
pointed at the fixture and `upsert_machine_label` stubbed. The interactive TTY guard fires
on piped stdin, so behavioral cases were driven through a real pseudo-TTY via a Python
`pty.fork()` harness (macOS `script -q` proved unreliable — it injects a spurious leading
EOF and echoes input, mangling multi-line/empty-line cases):
- **Quit-by-number** (index 4) → `No catalog written.`, exit 0. PASS
- **Quit-by-word** `q` → `No catalog written.`, exit 0. PASS
- **Enter-default** (empty line, host mapped to office) → menu shows
  `1) office   (this machine — default)`, resolves `TARGET_LOCATION=office`, no quit text. PASS
- **Create-new** (index 3) + `bad/name` (rejected with the `/`-rule reason) + `Good Name` →
  `Good Name/` directory created, `TARGET_LOCATION=Good Name`. PASS
- **No-default** (unmapped host) → no `(this machine — default)` marker; empty input
  re-prompts with `No default for this machine — please enter a number.` instead of
  defaulting. PASS
- Discovery ordering confirmed remembered-first then alphabetical; `.git/` and `docs/`
  correctly excluded (no catalogs, not map values).

## TTY / Test-Harness Limitation

The immediate-EOF behavioral case (pipe nothing → Quit) was **inconclusive** under the
Python pty harness because the pseudo-terminal stays open (no genuine Ctrl-D / `close()` of
the master is delivered to the child's `read` before the read-timeout), so the harness could
not force a true EOF on the menu read. The EOF-as-Quit path is instead verified by source
inspection plus the `grep -c 'if ! read -r choice; then'` == 1 assertion required by the
plan, and the create-new EOF branch shares the same `if ! read -r ...; then ... exit 0`
construct. Per the plan's documented fallback, the grep-based floor is the mandatory check
and the pseudo-TTY checks are best-effort; this single case falls back to the grep floor.

## Deviations from Plan

None — plan executed as written. (One naming nuance: the empty-input re-prompt message is
`No default for this machine — please enter a number.` exactly as specified in Pattern F;
no functional deviation.)

## Threat Surface

No new threat surface beyond the plan's `<threat_model>`:
- T-11-01 (create-new name) mitigated: routed through `validate_computer_name_quiet` in a
  re-prompt loop before `mkdir -p` — verified by the `bad/name`-rejected behavioral case.
- T-11-02 (map read-loop) and T-11-03 (discovery glob) accepted as planned; reads only
  top-level dir names and TAB-split map values, no file contents.

## Known Stubs

None. The function is fully wired except for the deliberate, plan-scoped non-wiring: the
main block still calls the legacy path; rewiring `select_computer` into the main block is
Plan 02's explicit responsibility (stated in the plan objective).

## Self-Check: PASSED

- FOUND: update-list.sh (contains `select_computer()`, committed at HEAD)
- FOUND: .planning/phases/11-computer-selection-cli/11-01-SUMMARY.md
- FOUND commit: d1cf891 (Task 1)
- FOUND commit: 89e6e68 (Task 2)
