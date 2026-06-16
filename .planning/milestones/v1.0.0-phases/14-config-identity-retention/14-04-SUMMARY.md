---
phase: 14-config-identity-retention
plan: "04"
subsystem: config
tags: [config, xdg, toml, git-validation, precedence, cli]
dependency_graph:
  requires: [14-01, 14-02, 14-03]
  provides: [maccat.config]
  affects: [phase-16-cli]
tech_stack:
  added: []
  patterns:
    - XDG config path direct construction (no platformdirs)
    - TOML hand-emit with backslash-first escaping
    - atomic tempfile+rename for config.toml write
    - subprocess git rev-parse for repo validation (list form, shell=False)
key_files:
  created:
    - src/maccat/config.py
    - tests/test_config.py
  modified: []
decisions:
  - "Config path: XDG_CONFIG_HOME env override, fallback to Path.home()/.config/maccat/config.toml — no platformdirs"
  - "tomllib is read-only; config init hand-emits TOML with _toml_string escaping (backslash first)"
  - "resolve_archive_days lives in config.py (argument resolution logic, not domain logic)"
  - "Test assertion for tilde expansion: load_config calls expanduser() so test asserts expanded path"
metrics:
  duration: 12
  completed: "2026-06-14"
  tasks_completed: 1
  files_changed: 2
---

# Phase 14 Plan 04: config.py — XDG path, precedence resolution, git-repo validation Summary

**One-liner:** Config resolution chain (flag > MACCAT_CATALOG_DIR env > config.toml > actionable error) with XDG path, tomllib loading, atomic TOML write, and subprocess git-repo validation.

## What Was Built

`src/maccat/config.py` — the configuration backbone for maccat. Implements:

- `_default_config_path()`: constructs `${XDG_CONFIG_HOME:-$HOME/.config}/maccat/config.toml` directly without platformdirs
- `Config` dataclass: `catalog_dir: Path | None = None`
- `load_config(config_path)`: tomllib binary-mode read, flat `catalog_dir` key, expanduser on value
- `resolve_catalog_repo(flag_val, config)`: CFG-01 three-level precedence chain — flag wins > `MACCAT_CATALOG_DIR` env > config file > `SystemExit` with actionable message listing all three options; flag value never written back (CFG-03)
- `_is_git_repo(path)` / `_has_git_remote(path)`: private subprocess helpers using list form, shell=False
- `validate_catalog_repo(catalog_repo)`: CFG-06 fail-fast on missing dir or non-git repo; warn-and-continue on absent remote
- `_toml_string(s)`: backslash-first TOML basic string escaping (prevents injection T-14-12)
- `write_config(config_path, catalog_dir)`: atomic tempfile + rename (T-14-13)
- `config_init(config_path)`: TTY guard, interactive loop with EOF → `SystemExit("\nAborted.")` — no `continue` anti-pattern (T-14-16)
- `config_show(flag_val, config, config_path)`: precedence-labeled output for all three sources
- `resolve_archive_days(flag_val, default)`: zsh `resolve_archive_retention` analog — non-TTY default, interactive prompt, validates >= 1

`tests/test_config.py` — 42 tests in 6 classes covering all CFG requirements.

## Test Results

```
179 passed in 0.54s  (full suite — 42 new config tests + 137 prior)
mypy --strict src/maccat/config.py: no issues found
ruff check src/maccat/config.py tests/test_config.py: all checks passed
```

## Precedence Verification (three independent tests)

| Test | Source that wins | Result |
|------|-----------------|--------|
| `test_flag_wins_over_env_and_config` | flag | flag_dir path returned |
| `test_env_wins_over_config` | MACCAT_CATALOG_DIR env | env_dir path returned |
| `test_config_used_when_no_flag_or_env` | config file | cfg_dir path returned |
| `test_all_absent_raises_systemexit` | none | SystemExit with all three options listed |

## CFG-03 Verification

`test_flag_not_written_back`: patches `write_config` and asserts it is never called when `resolve_catalog_repo` is called with a `flag_val`.

## CFG-06 Verification

| Test | Scenario | Outcome |
|------|----------|---------|
| `test_missing_dir_raises` | nonexistent path | `SystemExit` with "not found" + remediation hint |
| `test_non_git_dir_raises` | plain directory (no .git) | `SystemExit` with "not a git repository" + remediation hint |
| `test_valid_git_no_remote_warns` | git_repo fixture (no remote) | WARNING printed, no exception |
| `test_valid_git_with_remote_silent` | git repo with origin | no output, no exception |

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1: config.py + tests | 2cf4476 | src/maccat/config.py, tests/test_config.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion for tilde-expanded path**
- **Found during:** Task 1 (first test run)
- **Issue:** Test `test_tilde_in_path_is_expanded` asserted `cfg.catalog_dir == Path("~/myrepo")` but `load_config` calls `expanduser()` as specified in the plan's behavior spec — the stored value IS expanded.
- **Fix:** Updated test assertion to compare against the expanded path (`Path(str(tmp_path) + "/myrepo")`).
- **Files modified:** tests/test_config.py
- **Commit:** 2cf4476 (same commit, fixed before commit)

**2. [Rule 2 - Lint] Import block ordering (ruff I001)**
- **Found during:** Task 1 (ruff check)
- **Issue:** Ruff I001 flagged unsorted import blocks in both config.py and test_config.py.
- **Fix:** `ruff check --fix` auto-corrected import ordering.
- **Files modified:** src/maccat/config.py, tests/test_config.py
- **Commit:** 2cf4476

## Known Stubs

None — all functions are fully implemented. `config_init` and `config_show` are complete interactive/display functions. The git commit section in `rename_machine` (Phase 16 stub in `identity.py`) is pre-existing from plan 14-03, not introduced by this plan.

## Threat Flags

No new threat surface introduced beyond what the plan's threat model covers:
- T-14-11 (path traversal): mitigated via `.expanduser().resolve()`
- T-14-12 (TOML injection): mitigated via `_toml_string` backslash-first escaping
- T-14-13 (atomic write): mitigated via tempfile + rename
- T-14-15 (subprocess injection): mitigated via list form, shell=False
- T-14-16 (non-TTY hang): mitigated via `sys.stdin.isatty()` guard at `config_init` entry

## Self-Check: PASSED

- [x] `src/maccat/config.py` exists: FOUND
- [x] `tests/test_config.py` exists: FOUND
- [x] Commit 2cf4476 exists: FOUND
- [x] 179 tests pass
- [x] mypy --strict clean
- [x] ruff clean
- [x] All Phase 14 modules import cleanly
