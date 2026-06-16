---
phase: 26-picker-cli-wiring-integration
verified: 2026-06-16T21:52:57Z
status: passed
score: 7/7
overrides_applied: 0
---

# Phase 26: Picker + CLI Wiring + Integration Verification Report

**Phase Goal:** `maccat reinstall` is a working subcommand that resolves a catalog, generates `reinstall.sh`, and prints its path
**Verified:** 2026-06-16T21:52:57Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `maccat reinstall --from path/to/catalog.txt` writes reinstall.sh to cwd, prints its absolute path, exits 0 | VERIFIED | `test_from_path_writes_reinstall_sh` passes; `run_reinstall` line 79-82: `Path.cwd() / "reinstall.sh"`, `write_text`, `os.chmod`, `print(str(output_path.resolve()))` |
| 2 | reinstall.sh is mode 0o644 (rw-r--r--) and was never subprocess-run | VERIFIED | `os.chmod(output_path, 0o644)` at line 81 of reinstall/cli.py; no subprocess import anywhere in picker.py or reinstall/cli.py; `test_file_mode_is_0o644` passes |
| 3 | reinstall.sh opens with `#!/usr/bin/env bash` and a provenance header naming the source catalog and generation date | VERIFIED | `emit_reinstall_script(source_name=catalog_path.name, generated=date.today().strftime("%Y-%m-%d"))` in reinstall/cli.py line 73-77; `test_shebang_is_present` and `test_reinstall_sh_contains_generated_on_header` pass |
| 4 | `maccat reinstall` without `--from` invokes select_computer and picks the newest catalog by filename timestamp (not mtime) | VERIFIED | `_find_newest_catalog` uses `cf.timestamp > best_ts` (lexicographic string compare on 14-digit timestamps); `test_picker_mode_writes_reinstall_sh_from_newest` confirms newer catalog wins; `test_picker_mode_quit_writes_nothing` confirms None return on quit |
| 5 | The 13-step catalog-gen path in cli.py run() is byte-behavior identical for non-reinstall invocations | VERIFIED | Steps 6-13 in cli.py lines 285-353 are intact; `test_non_reinstall_invocation_unchanged` calls `run()` with `--no-commit --computer personal` and asserts `git_pull` called, no reinstall.sh written; all 7 step-comment labels present |
| 6 | `--rename` combined with `reinstall` exits non-zero with a clear error message | VERIFIED | Both dispatch points (4b line 248-249, 4d line 267-268) call `sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")`; `test_reinstall_rename_mutual_exclusion` asserts `SystemExit` with non-zero code |
| 7 | Integration test passes: reinstall.sh exists, mode 0o644, correct shebang + provenance header, gen path not triggered, --rename guard not fired | VERIFIED | 31 tests in test_reinstall_cli.py and test_picker_and_reinstall_cli.py all PASS; full suite 553 passed |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/maccat/reinstall/picker.py` | `resolve_catalog_path(args, catalog_repo) -> Path \| None` | VERIFIED | Exists, substantive (167 lines), exports `resolve_catalog_path` and private `_find_newest_catalog`; `from maccat.naming import parse_catalog_filename` at module level (safe per plan note); maccat.identity deferred inside picker branch |
| `src/maccat/reinstall/cli.py` | `run_reinstall(args, catalog_repo) -> None` orchestrator | VERIFIED | Exists, substantive (83 lines), full pipeline implemented; no maccat.* module-level imports; all imports deferred inside `run_reinstall` body |
| `src/maccat/cli.py` | reinstall subparser + two-point dispatch in run() | VERIFIED | `dest="from_path"` at line 113; `reinstall_parser` added at line 106-143; 4b dispatch at line 247, 4d dispatch at line 266; both deferred `from maccat.reinstall.cli import run_reinstall` inside their respective if-blocks |
| `tests/reinstall/test_reinstall_cli.py` | `TestReinstallSubcommand` integration tests | VERIFIED | Exists with 14 test methods in `TestReinstallSubcommand`; all 14 pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/maccat/cli.py run() step 4b` | `src/maccat/reinstall/cli.py run_reinstall` | deferred import inside if-block | WIRED | `from maccat.reinstall.cli import run_reinstall` at line 250; `run_reinstall(args)` at line 251 |
| `src/maccat/cli.py run() step 4d` | `src/maccat/reinstall/cli.py run_reinstall` | deferred import inside if-block | WIRED | `from maccat.reinstall.cli import run_reinstall` at line 269; `run_reinstall(args, catalog_repo=catalog_repo)` at line 270 |
| `src/maccat/reinstall/cli.py run_reinstall` | `src/maccat/reinstall/picker.py resolve_catalog_path` | direct call | WIRED | `from maccat.reinstall.picker import resolve_catalog_path` line 57; `catalog_path = resolve_catalog_path(args, catalog_repo=catalog_repo)` line 59 |
| `src/maccat/reinstall/cli.py run_reinstall` | `reinstall.sh` on disk | `Path.write_text` + `os.chmod` | WIRED | `output_path.write_text(script, encoding="utf-8")` line 80; `os.chmod(output_path, 0o644)` line 81 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `reinstall/cli.py run_reinstall` | `script` | `emit_reinstall_script(catalog, source_name=..., generated=...)` | Yes — parsed catalog fed into emitter, returns real script string starting with `#!/usr/bin/env bash` | FLOWING |
| `reinstall/picker.py _find_newest_catalog` | `best_path` | `folder.glob("mac-software-list-*.txt")` + `parse_catalog_filename` lexicographic compare | Yes — real filesystem glob, not hardcoded | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `maccat reinstall --help` shows subcommand | `./venv/bin/python -m maccat --help` | Output includes `{config,reinstall}` and `reinstall  Generate reinstall.sh from a catalog` | PASS |
| subparser parses `--from PATH` into `from_path` | `python -c "from maccat.cli import _build_parser; p = _build_parser(); args = p.parse_args(['reinstall', '--from', '/tmp/x']); print(args.from_path, args.subcommand)"` | `/tmp/x reinstall` | PASS |
| Full test suite (553 tests) | `./venv/bin/python -m pytest tests/ -q` | `553 passed in 12.56s` | PASS |
| mypy --strict on modified files | `./venv/bin/mypy --strict src/maccat/reinstall/picker.py src/maccat/reinstall/cli.py src/maccat/cli.py` | `Success: no issues found in 3 source files` | PASS |
| ruff check on modified files | `./venv/bin/ruff check src/maccat/reinstall/picker.py src/maccat/reinstall/cli.py src/maccat/cli.py tests/reinstall/test_reinstall_cli.py` | `All checks passed!` | PASS |

### Probe Execution

No probe scripts declared in PLAN.md or found at `scripts/*/tests/probe-*.sh`. Skipped.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RST-01 | 26-01-PLAN.md | `maccat reinstall` generates a `reinstall.sh` from a catalog, prints its output path, never auto-executes; mode 0o644 | SATISFIED | `run_reinstall` writes file, sets `os.chmod(output_path, 0o644)`, calls `print(str(output_path.resolve()))`, no subprocess calls; truth 1 and 2 VERIFIED |
| RST-02 | 26-01-PLAN.md | `--from PATH` selects explicit catalog; if omitted, interactive picker selects computer and uses newest catalog; `--computer NAME` flows through | SATISFIED | `resolve_catalog_path` handles both branches; `--computer` mirrored onto reinstall subparser with `default=argparse.SUPPRESS`; truths 1 and 4 VERIFIED |

### Anti-Patterns Found

No `TBD`, `FIXME`, or `XXX` markers found in any file modified by this phase. No `TODO`, `HACK`, or `PLACEHOLDER` markers found. No stub patterns (empty returns, hardcoded empty arrays) found in implementation files. No subprocess calls in `picker.py` or `reinstall/cli.py`.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

### Human Verification Required

None. All must-haves are verifiable programmatically. The phase produces no UI, no visual output, and no external service integration. The full test suite (553 tests) including 31 new reinstall-specific tests covers all observable behaviors.

### Gaps Summary

No gaps. All 7 must-have truths are VERIFIED against the codebase. All artifacts exist, are substantive, and are wired. Both requirement IDs (RST-01, RST-02) are satisfied. The test suite passes clean at 553 tests with mypy --strict and ruff clean.

---

_Verified: 2026-06-16T21:52:57Z_
_Verifier: Claude (gsd-verifier)_
