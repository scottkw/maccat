---
phase: 26-picker-cli-wiring-integration
reviewed: 2026-06-16T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/maccat/reinstall/picker.py
  - src/maccat/reinstall/cli.py
  - src/maccat/cli.py
  - tests/reinstall/test_reinstall_cli.py
  - tests/reinstall/test_picker_and_reinstall_cli.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
---

# Phase 26: Code Review Report (Iteration 2)

**Reviewed:** 2026-06-16
**Depth:** standard
**Files Reviewed:** 5
**Status:** clean

## Summary

Re-review (iteration 2) of the auto fix+review loop. The four warnings raised in
iteration 1 (WR-01 through WR-04) were re-examined against the current source,
each fix was traced through its code path, the specific failure modes called out
in the re-review prompt were probed directly, and the full test suite was run.

**No new defects found.** All four fixes are correct and introduce no regressions.
The 13-step generation path and the two-point reinstall dispatch remain intact
(no double-fire, no fall-through). Accepted Info items IN-01 and IN-02 were treated
as accepted and are not re-reported.

### Verification performed

**WR-03 (argparse precedence — SUPPRESS default):** Confirmed empirically with
`_build_parser().parse_args(...)` across all six relevant invocation shapes:
- `maccat reinstall` -> `computer=None` (top-level `--computer` default supplies the
  attribute; subparser SUPPRESS leaves it untouched). **No namespace-attribute-missing
  crash** when neither side supplies `--computer`.
- `maccat reinstall --computer X` -> `computer=X` (post-subcommand parses, not
  "unrecognized arguments").
- `maccat --computer Y reinstall` -> `computer=Y` (SUPPRESS does not clobber the
  pre-subcommand value).
- `maccat --computer Y reinstall --computer X` -> `computer=X` (post-subcommand wins,
  predictable left-to-right precedence).
- `from_path` is absent on non-reinstall namespaces, but every read of
  `args.from_path` is guarded by `args.subcommand == "reinstall"` first and Python
  `and` short-circuits, so no AttributeError is reachable (cli.py:247).

**WR-04 (read-only picker, existing-folder resolution):** Verified directly:
- Unknown `--computer GhostMac` -> clean `SystemExit` with actionable message;
  no stray folder created; no `machine-labels.tsv` written
  (`test_unknown_computer_fails_clean_no_stray_dir` passes).
- Name present in `machine-labels.tsv` but with no on-disk catalog folder -> fails
  cleanly via `_find_newest_catalog` returning `None` ->
  `ERROR: No catalog files found in ...`; confirmed no stray folder is created
  (`folder.glob()` does not raise on a nonexistent directory).
- Interactive path (no `--computer`) still routes to
  `select_computer(..., computer_name=None)` per the locked CONTEXT decision; quit
  returns `None` and writes nothing (`test_picker_mode_quit_writes_nothing` passes).

**WR-01 (clean error on unreadable / unparseable catalog):** Confirmed the `--from`
branch probes `os.access(p, os.R_OK)` after `is_file()` and exits with
`ERROR: Catalog file is not readable` (`test_exits_cleanly_on_unreadable_file`
passes, skipped only under root). The catch-all `try/except OSError` around
`parse_catalog` in `run_reinstall` converts a mid-pipeline read failure into the
project's `ERROR:` convention rather than a traceback.

**Gen path + two-point dispatch intact:**
- `--from` mode: 4b dispatch fires and returns before repo resolution (4c) and the
  picker dispatch (4d) — single fire.
- Picker mode: 4b skipped (`from_path is None`), 4c validates repo, 4d fires and
  returns — single fire, no fall-through to generation.
- Non-reinstall invocation: both 4b and 4d skipped; generation path reaches
  `git_pull` (`test_non_reinstall_invocation_unchanged` asserts `git_pull` called
  once and no `reinstall.sh` written).
- `--rename` x reinstall and `--rename`/`--computer` x `config` guards all fire
  before their respective early returns (covered by tests).

### Tooling results

- `pytest tests/reinstall/...` — 31 passed.
- `pytest` (full suite) — 553 passed.
- `mypy --strict` on all three source files — Success, no issues.
- `ruff check` on all three source files — All checks passed.
- No debug artifacts, TODO/FIXME, or empty catch blocks in the changed source.

## Narrative Findings (AI reviewer)

No Critical, Warning, or Info findings. All four prior warnings are correctly
resolved and no new defects were introduced.

---

_Reviewed: 2026-06-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
