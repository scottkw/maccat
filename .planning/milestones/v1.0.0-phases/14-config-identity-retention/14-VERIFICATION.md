---
phase: 14-config-identity-retention
verified: 2026-06-14T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 14: Config, Identity, Retention Verification Report

**Phase Goal:** The tool resolves its catalog repo from config or flag, presents the correct computer-folder selection menu, manages identity/rename, and runs retention/prune — all without touching a live catalog repo.
**Verified:** 2026-06-14
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `config init` writes `~/.config/maccat/config.toml` with a validated catalog-repo path; `config show` prints the resolved effective config including the precedence winner (flag > env > file > error) | ✓ VERIFIED | `config_init` in config.py (L250-302): TTY guard, interactive loop, `_is_git_repo` validation, atomic `write_config`; `config_show` (L310-353): prints source label for all three tiers; 6 TestConfigShow tests pass; 5 TestWriteConfig tests pass; behavioral smoke test confirms round-trip |
| 2 | The computer-folder selection menu shows existing folders + create-new + Quit, remembers the previous folder as the Enter default, and never hangs in a non-TTY context (piped input fails fast with a clear error) | ✓ VERIFIED | `select_computer` in identity.py (L292-436): sys.stdin.isatty() guard before any input(); saved_folder TSV lookup + promotion to position 0; numbered menu with create-new + Quit; EOF routes through Quit branch; 6 TestSelectComputer tests + TestSelectComputerEofMessage pass; non-TTY smoke test confirmed: `SystemExit: ERROR: No computer selected and stdin is not a TTY. Pass --computer "Name".` |
| 3 | `--computer "Name"` with `--personal`/`--office`/`--machine` aliases works non-interactively; mutual-exclusion error fires when more than one selecting flag is passed (NOTE: Phase 14 implements the pure resolver `resolve_computer_selection` in identity.py with mutual-exclusion SystemExit; the argparse PARSER construction that calls it is intentionally Phase 16) | ✓ VERIFIED | `resolve_computer_selection` (identity.py L81-131): counts truthy flags with `sum([personal, office, bool(machine), bool(computer)])`; count>1 → `SystemExit("ERROR: --personal, --office, --computer, and --machine are mutually exclusive.")`; count==0 → None; count==1 → validated resolved value; 11 TestResolveComputerSelection tests pass; SC3 behavioral smoke test confirmed all four aliases + mutual exclusion |
| 4 | `retain_newest_per_host` keeps ALL files tied for newest (two-pass, not max()); `prune_old_archives` skips (never deletes) files with unparseable timestamps; `--archive-days N` controls the cutoff | ✓ VERIFIED | `retain_newest_per_host` (retention.py L37-87): two-pass: pass 1 builds `newest: dict[str,str]`, pass 2 keeps `cf.timestamp == newest.get(cf.machine, "")`; tied-newest correctness: both files share the same max timestamp so both pass; `prune_old_archives` (L90-147): unparseable → warn + continue, never unlink; int comparison for cutoff; 8 TestRetainNewestPerHost + 9 TestPruneOldArchives pass; all safety invariants confirmed by spot-checks |
| 5 | `rename_machine` hard refuses to clobber an existing folder name and exits cleanly; atomic `machine-labels.tsv` writes preserve existing comments and blank lines; Ctrl-D at any prompt exits cleanly without traceback or infinite loop | ✓ VERIFIED | `rename_machine` (identity.py L444-625): Guard 3 at L543-548: `if new_dir.exists(): raise SystemExit("ERROR: A computer named '{new_name}' already exists. Refusing to merge.")` before any rename; `upsert_machine_label` (L231-284): reads existing lines preserving blank/comment; single atomic `_atomic_write_lines` call; all EOFError handlers return None (never continue); 5 TestRenameMachine + 7 TestUpsertMachineLabel tests pass; clobber smoke test + upsert comment preservation smoke test confirmed |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/maccat/naming.py` | CatalogFilename frozen dataclass, parse_catalog_filename, make_catalog_filename | ✓ VERIFIED | 72 lines; exports all three; frozen=True; regex `[^\[\]]+` prevents bracket injection; returns None for non-match, never raises |
| `tests/test_naming.py` | Unit tests for naming.py | ✓ VERIFIED | 21 tests, all pass; covers valid filenames, spaces in machine name, brackets return None, digit-count None, gitkeep None, round-trip, immutability, hashability |
| `tests/conftest.py` | git_repo and catalog_repo fixtures; tmp_json preserved | ✓ VERIFIED | tmp_json fixture intact (L11-19); git_repo (L23-40): subprocess git init + user config, returns tmp_path; catalog_repo (L44-55): builds on git_repo, creates personal/ with one catalog file; deferred import of make_catalog_filename inside fixture |
| `src/maccat/retention.py` | retain_newest_per_host, prune_old_archives, cutoff_yyyymmdd | ✓ VERIFIED | 148 lines; all three functions present; two-pass algorithm; unparseable-skip guard; int comparison for cutoff; OSError warn-and-continue on unlink |
| `tests/test_retention.py` | TDD tests for retention — written RED before implementation | ✓ VERIFIED | 20 tests (including CR-02 int-comparison guard tests and WR-01 OSError warn-and-continue), all pass |
| `src/maccat/identity.py` | resolve_computer_selection, validate_computer_name, validate_computer_name_quiet, discover_computer_folders, select_computer, upsert_machine_label, rename_machine | ✓ VERIFIED | 625 lines; all seven exports present; Phase 16 stub comment at L625; auto_commit=False parameter on rename_machine |
| `tests/test_identity.py` | Unit + behavioral tests for identity.py | ✓ VERIFIED | 48 tests across 8 classes (including TestIterTsvEntries, TestSelectComputerEofMessage, TestRenameMachineFolderMoveGuard added beyond plan baseline), all pass |
| `src/maccat/config.py` | Config dataclass, load_config, resolve_catalog_repo, validate_catalog_repo, config_init, config_show, _default_config_path | ✓ VERIFIED | 409 lines; all exports present; XDG path construction without platformdirs; tomllib binary-mode read; atomic write; git rev-parse --show-toplevel toplevel check (stronger than --git-dir per WR-06) |
| `tests/test_config.py` | Unit tests for config.py — CFG-01 through CFG-06 | ✓ VERIFIED | 46 tests across 6 classes (including WR-05 EOFError exit message test and WR-06 subdir rejection test), all pass |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `retention.py` | `naming.py` | `from maccat.naming import parse_catalog_filename` | ✓ WIRED | retention.py L19: `from maccat.naming import parse_catalog_filename`; called at L67, L78, L122 |
| `identity.py` | `naming.py` | `from maccat.naming import make_catalog_filename, parse_catalog_filename` | ✓ WIRED | identity.py L23: import confirmed; parse_catalog_filename used in rename_machine L584; make_catalog_filename used at L594 |
| `resolve_computer_selection` | `validate_computer_name` | direct call inside resolver | ✓ WIRED | identity.py L126-130: machine branch calls validate_computer_name(machine); computer branch calls validate_computer_name(computer) |
| `tests/test_identity.py` | `conftest.py catalog_repo fixture` | pytest fixture injection | ✓ WIRED | test_identity.py L200: `def test_enter_with_saved_folder_returns_saved(self, catalog_repo: Path, ...)` |
| `config.py resolve_catalog_repo` | `MACCAT_CATALOG_DIR` env var | `os.environ.get('MACCAT_CATALOG_DIR')` | ✓ WIRED | config.py L122: `env_val = os.environ.get("MACCAT_CATALOG_DIR")`; test_env_var_name_is_maccat_catalog_dir confirms wrong name rejected |
| `config.py _default_config_path` | `XDG_CONFIG_HOME` env var | `os.environ.get('XDG_CONFIG_HOME')` | ✓ WIRED | config.py L39: `xdg = os.environ.get("XDG_CONFIG_HOME")`; TestResolveConfigPath::test_xdg_override passes |
| `config.py validate_catalog_repo` | git subprocess | `subprocess.run(["git", "rev-parse", "--show-toplevel"], ...)` | ✓ WIRED | config.py L157-170: `_is_git_repo` uses --show-toplevel (not --git-dir) to verify path IS the repo root; TestValidateCatalogRepo::test_subdir_of_parent_repo_rejected passes |

### Data-Flow Trace (Level 4)

All Phase 14 modules are pure logic, file I/O, and subprocess delegation — no dynamic rendering components. Data flows are function-argument chains, not UI component props. Level 4 does not apply.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| All Phase 14 modules import cleanly | `PYTHONPATH=src ./venv/bin/python -c "from maccat.naming import ...; from maccat.retention import ...; from maccat.identity import ...; from maccat.config import ..."` | "All Phase 14 modules import cleanly" | ✓ PASS |
| SC3: mutual exclusion fires | `resolve_computer_selection(computer=None, personal=True, office=True, machine=None)` | `SystemExit: ERROR: --personal, --office, --computer, and --machine are mutually exclusive.` | ✓ PASS |
| SC3: flag resolution | `resolve_computer_selection(personal=True, ...)` == "personal" | "personal" | ✓ PASS |
| Non-TTY fast-fail on select_computer | piped stdin + `select_computer(d)` | `SystemExit: ERROR: No computer selected and stdin is not a TTY. Pass --computer "Name".` | ✓ PASS |
| refuse-clobber in rename_machine | existing new_dir + `rename_machine(d)` | `SystemExit: ERROR: A computer named 'NewName' already exists. Refusing to merge. Nothing renamed.` | ✓ PASS |
| upsert_machine_label preserves comments | pre-populated TSV with comments + blank lines | comments and blank lines intact after upsert | ✓ PASS |
| config precedence: flag > env > config | all three sources set, flag_val provided | flag_dir path returned | ✓ PASS |
| write_config/load_config round-trip | write_config then load_config | identical catalog_dir Path | ✓ PASS |
| Full test suite | `PYTHONPATH=src ./venv/bin/pytest tests/ --tb=short` | 194 passed in 0.69s | ✓ PASS |

### Probe Execution

No probe scripts defined for Phase 14. Step 7c: SKIPPED (no `scripts/*/tests/probe-*.sh` files; phase delivers library modules, not a runnable CLI entry point — that is Phase 16).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| CFG-01 | 14-04 | Catalog-repo location resolved by flag > env > config file > clear error | ✓ SATISFIED | `resolve_catalog_repo` three-level chain; 7 tests in TestResolveCatalogRepo pass; behavioral smoke test confirmed |
| CFG-02 | 14-04 | Config at `${XDG_CONFIG_HOME:-$HOME/.config}/maccat/config.toml` | ✓ SATISFIED | `_default_config_path()` constructs XDG path directly without platformdirs; test_xdg_override + test_default_path_uses_home_config pass |
| CFG-03 | 14-04 | `--catalog-dir` flag never written back to config file | ✓ SATISFIED | `resolve_catalog_repo` never calls `write_config`; test_flag_not_written_back mocks write_config and asserts never called |
| CFG-04 | 14-04 | `config init` interactively captures and validates; `config show` prints resolved config | ✓ SATISFIED | `config_init` (interactive loop + validation + atomic write); `config_show` (precedence-labeled output); 6 TestConfigShow tests pass |
| CFG-05 | 14-04 | App repo separated from catalog repo — never assumes catalog lives next to executable | ✓ SATISFIED | `_default_config_path` never uses `Path(__file__).parent` or `os.getcwd()`; config.py docstring documents this explicitly |
| CFG-06 | 14-04 | Fails fast when catalog dir missing or not git repo; warns-and-continues when no remote | ✓ SATISFIED | `validate_catalog_repo`: SystemExit for missing dir and non-git dir; prints WARNING for no remote; 6 TestValidateCatalogRepo tests pass |
| OPS-01 | 14-03 | Always-shown computer-folder selection menu with TTY guard | ✓ SATISFIED | `select_computer` menu always shown when computer_name is None; sys.stdin.isatty() guard before any input(); 6 TestSelectComputer tests pass |
| OPS-02 | 14-03 | `--computer "Name"` with aliases and mutual-exclusion | ✓ SATISFIED | `resolve_computer_selection` pure function maps all four flags; mutual-exclusion SystemExit; 11 TestResolveComputerSelection tests pass; Phase 16 wires argparse dispatch |
| OPS-03 | 14-01 + 14-02 | Newest-per-machine retention: two-pass, tied-newest kept, unparseable skipped | ✓ SATISFIED | `retain_newest_per_host` two-pass algorithm; tied-newest correctness: equality check handles both tied files; 8 TestRetainNewestPerHost tests pass |
| OPS-04 | 14-02 | Archive prune at N days with `--archive-days N`; correct generate-then-sweep ordering | ✓ SATISFIED (Phase 14 scope) | `prune_old_archives` + `resolve_archive_days` implement the prune function and days resolver; generate-then-sweep ordering is Phase 16 CLI wiring (documented in Plan 02) |
| OPS-05 | 14-03 | `machine-labels.tsv` atomic writes preserving comments/blank lines | ✓ SATISFIED | `upsert_machine_label` + `_atomic_write_lines`: tempfile.mkstemp + Path.rename; reads existing content preserving blank/comment lines verbatim; 7 TestUpsertMachineLabel tests pass |
| OPS-07 | 14-03 | `--rename` with hard refuse-clobber guard, opt-out filename rewrite, TSV update | ✓ SATISFIED | `rename_machine`: Guard 3 is SystemExit (not warning); filename rewrite with collision guard; unconditional TSV atomic update; 6 TestRenameMachine tests + TestRenameMachineFolderMoveGuard pass |
| OPS-08 | 14-03 + 14-04 | Non-TTY never hangs, EOF exits cleanly, invalid input re-prompts | ✓ SATISFIED | TTY guards in select_computer, rename_machine, config_init; all EOFError handlers return None or raise SystemExit (no `continue` anti-pattern); TestSelectComputerEofMessage, TestResolveArchiveDays::test_interactive_eof passes |

### Anti-Patterns Found

No blockers found.

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `src/maccat/identity.py` | 625 | `# Phase 16: if auto_commit: git_commit_rename(...)` | INFO | Documented Phase 16 stub. auto_commit parameter exists (default False). Git commit is intentionally deferred — plan specifies this exactly. Not a TBD/FIXME/XXX marker. |

No TBD, FIXME, or XXX markers found in any Phase 14 source file.
No TODO/HACK/PLACEHOLDER markers found.
No `return null` / `return {}` / `return []` stubs in implementation code.
All tests use disposable fixtures (tmp_path, git_repo, catalog_repo) — no real personal/office directory references found.

### Human Verification Required

None. All success criteria are verifiable programmatically and have been verified.

---

## Gaps Summary

No gaps. All 5 success criteria are VERIFIED, all 13 requirement IDs are SATISFIED, all 9 required artifacts are substantive and wired, all key links are confirmed, all 194 tests pass, mypy --strict clean on all 4 modules, ruff clean on all 4 modules.

The single Phase 16 comment stub in `rename_machine` (git commit section) is an intentional, documented deferral specified by the plan — not a gap.

---

_Verified: 2026-06-14_
_Verifier: Claude (gsd-verifier)_
