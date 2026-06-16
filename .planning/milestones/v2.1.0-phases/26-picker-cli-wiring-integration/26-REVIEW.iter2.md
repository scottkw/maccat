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
  warning: 4
  info: 2
  total: 6
status: issues_found
---

# Phase 26: Code Review Report

**Reviewed:** 2026-06-16
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the Phase 26 `maccat reinstall` wiring: `picker.py::resolve_catalog_path`,
`reinstall/cli.py::run_reinstall`, and the two-point dispatch added to root `cli.py`.

The core safety invariants the prompt asked me to verify hold:

- **Criterion 3 (no gen-path regression): CONFIRMED.** `git diff d96e6c0 6b40888` shows
  the only changes to the non-reinstall path are `load_config()` and the `auto_commit`
  assignment moving by a few lines (semantically identical). All reinstall dispatch
  branches are gated on `args.subcommand == "reinstall"`, which is `None` on the gen
  path. The `test_non_reinstall_invocation_unchanged` test passes and exercises the full
  gen path. No byte-behavior change for non-reinstall invocations.
- **Two-point dispatch cannot double-fire or fall through.** 4b is gated on
  `subcommand == "reinstall" and from_path is not None` and `return`s; 4d is gated on
  `subcommand == "reinstall"` and `return`s. In `--from` mode 4b returns before 4d is
  reached; in picker mode 4b is skipped and 4d returns before the `--rename` short-circuit
  and gen path. Verified by argparse namespace inspection.
- **0o644 + never-subprocess-run: CONFIRMED.** `run_reinstall` calls
  `os.chmod(output_path, 0o644)` explicitly and contains no `subprocess`/`os.system`/
  `exec` call. The file is written and its path printed only.
- **Picker-quit (None) handling: CONFIRMED.** `select_computer` → `None` propagates
  through `resolve_catalog_path` → `run_reinstall`, which returns before writing. Tested.
- **No `or {}`-style silent fallback** found in any of the three source files.
- **mypy --strict: clean** on all three source files. **Reinstall test suite: 23 passed.**

The findings below are graceful-degradation, usability, and test-coverage defects. None
are data-loss or security issues, so there are no BLOCKERs — but WR-01 is a genuine
ungraceful-crash path the prompt explicitly asked about.

## Warnings

### WR-01: Unreadable `--from` file crashes with a raw traceback instead of a clean error

**File:** `src/maccat/reinstall/picker.py:101-105` (and `reinstall/cli.py:63`)
**Issue:** The `--from` branch validates only `p.is_file()`. `Path.is_file()` returns
`True` for a regular file the user cannot read (e.g. mode `0o000`). I verified this:
`resolve_catalog_path` returns the path for a `0o000` file, after which
`parse_catalog(catalog_path)` calls `path.read_text(encoding="utf-8")`, which raises an
uncaught `PermissionError` mid-pipeline — a raw Python traceback, not the project's
`ERROR: ...` convention. The prompt explicitly calls out that "a missing file must fail
cleanly not crash" and lists "unreadable paths" for error-clarity review. Missing/
non-file paths are handled cleanly; the unreadable case is not.
**Fix:** Add an explicit readability probe with a clean exit, e.g. in the `--from` branch:
```python
if args.from_path is not None:
    p = Path(args.from_path).expanduser().resolve()
    if not p.is_file():
        sys.exit(f"ERROR: Catalog file not found or not a regular file: {p}")
    if not os.access(p, os.R_OK):
        sys.exit(f"ERROR: Catalog file is not readable: {p}")
    return p
```
(Alternatively, wrap `parse_catalog` in `run_reinstall` to convert `OSError` into a
`sys.exit("ERROR: ...")`.) Add a test that chmods a fixture to `0o000` and asserts a
clean `SystemExit`.

### WR-02: Picker-mode reinstall dispatch (step 4d) has no integration test through `run()`

**File:** `src/maccat/cli.py:239-244`; tests in
`tests/reinstall/test_reinstall_cli.py`
**Issue:** Every integration test in `test_reinstall_cli.py` uses `--from`, which exits at
4b and never reaches 4c/4d. The picker-mode branch (4c repo resolve/validate → 4d
`run_reinstall(args, catalog_repo=catalog_repo)`) — the more complex path that depends on
`resolve_catalog_repo`, `validate_catalog_repo`, and `args.computer` being present on the
namespace — is exercised only via direct calls to `resolve_catalog_path`/`run_reinstall`
in the unit file, never through `run()`. The wiring (4d firing, `catalog_repo` threading,
`args.computer` reachability) could regress silently with all tests green.
**Fix:** Add an integration test that sets `MACCAT_CATALOG_DIR`, runs
`["maccat", "reinstall"]` with `select_computer` mocked to return a folder name containing
a fixture catalog, and asserts `reinstall.sh` is written from the newest catalog in that
folder. Also add a `["maccat", "reinstall"]` case where `select_computer` returns `None`
(quit) and assert no file written and clean return.

### WR-03: `maccat reinstall --computer NAME` fails with "unrecognized arguments"

**File:** `src/maccat/cli.py:106-116` (subparser) and `src/maccat/reinstall/picker.py:116`
**Issue:** `picker.py` picker branch reads `args.computer` and forwards it to
`resolve_computer_selection(computer=args.computer)`, and the `resolve_catalog_path`
docstring documents a `--computer` interaction. But the `reinstall` subparser defines only
`--from`; `--computer` lives on the top-level parser. I verified that
`maccat reinstall --computer x` exits with `error: unrecognized arguments: --computer x`,
while `maccat --computer x reinstall` works. The documented/natural invocation order is
broken, so the picker's pre-selection feature is effectively unreachable for users who
type the flag after the subcommand. (No `AttributeError` occurs — `args.computer` is
always present as `None` via the shared parser — so this is a usability defect, not a
crash.)
**Fix:** Either add `--computer` to the `reinstall` subparser (mirroring the top-level
flag, dest `computer`) so post-subcommand placement works, or remove the `args.computer`
forwarding and `--computer` mentions from `picker.py`/its docstring if pre-selection is
not a Phase 26 feature. Document the supported order explicitly in `--help`.

### WR-04: Picker-mode reinstall mutates the catalog repo (mkdir + machine-labels.tsv) for a read-only operation

**File:** `src/maccat/reinstall/picker.py:114-122`
**Issue:** Reinstall is specified as read-only (parse → emit → write `reinstall.sh` to
cwd; never touches the catalog repo). But the picker branch reuses
`select_computer(catalog_repo, computer_name=...)`, whose flag path (`computer_name is not
None`) does `(catalog_repo / computer_name).mkdir(parents=True, exist_ok=True)` and
`upsert_machine_label(...)` (writes `machine-labels.tsv`), and whose interactive
create-new branch also mkdirs and upserts. So `maccat reinstall` (no `--from`) can create
a new empty computer folder and rewrite the labels TSV as a side effect — and if a new
folder is created it then immediately `sys.exit`s with "No catalog files found", leaving a
stray empty directory and a modified TSV behind. This is a surprising mutation for a
catalog-reading command.
**Fix:** For reinstall, restrict selection to *existing* catalog folders without
mutating: either pass a read-only selection mode into the picker, or resolve the folder
from `discover_computer_folders(catalog_repo)` directly and `sys.exit` if the chosen name
has no folder, rather than going through the mkdir/upsert flag path. At minimum, document
the mutation if it is intended.

## Info

### IN-01: Non-deterministic tie-break when two catalogs share an identical timestamp

**File:** `src/maccat/reinstall/picker.py:51-53`
**Issue:** `_find_newest_catalog` uses strict `cf.timestamp > best_ts`, so when two files
in the folder have the same 14-digit timestamp (same machine running twice within one
second, or two machines committing into one folder) the winner is the first one yielded by
`folder.glob(...)`, whose iteration order is not guaranteed sorted. I reproduced this:
`[AAA]` and `[ZZZ]` with identical timestamps resolve to whichever glob yields first.
Impact is low (reinstall is read-only and retention normally keeps one-per-host), but the
selection is non-reproducible.
**Fix:** Make the tie-break deterministic, e.g. break ties by filename:
`if best_ts is None or (cf.timestamp, f.name) > (best_ts, best_path.name):`, or sort the
glob results before iterating.

### IN-02: Two identical `--rename`+reinstall guards duplicate the same string

**File:** `src/maccat/cli.py:220-225` (4b) and `src/maccat/cli.py:239-244` (4d)
**Issue:** Both dispatch branches repeat `if args.rename: sys.exit("ERROR: --rename
cannot be combined with the 'reinstall' subcommand.")` verbatim. Both are reachable and
correct (4b for `--from`, 4d for picker), so this is not dead code, but the duplicated
literal is a maintenance smell — a future edit to the message must touch two sites.
**Fix:** Hoist a single `if args.subcommand == "reinstall" and args.rename:` guard above
4b, or factor the message into a module constant. Low priority.

---

_Reviewed: 2026-06-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
