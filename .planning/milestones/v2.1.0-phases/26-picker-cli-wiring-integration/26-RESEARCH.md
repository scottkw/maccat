# Phase 26: Picker + CLI Wiring + Integration - Research

**Researched:** 2026-06-16
**Domain:** Python argparse subparser wiring, stdlib file I/O, in-process integration testing
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CLI Surface & Dispatch Point (RST-01/02)**
- Expose reinstall as a `reinstall` subparser (sibling to `config`, `dest="subcommand"`) with a `--from PATH` argument. NOT a top-level flag.
- Dispatch point in `run()`: after `load_config` → `resolve_catalog_repo` → `validate_catalog_repo`, and BEFORE the `--rename` short-circuit. The reinstall branch does its work and returns — it never falls through into the 13-step catalog-gen path.
- Catalog repo requirement: `--from PATH` is standalone and works against any catalog file WITHOUT requiring the configured catalog repo. Without `--from`, the repo IS required (the picker needs it). (Implication: if reinstall runs before `validate_catalog_repo` would reject a missing repo, ensure `--from` mode does not error on an absent/invalid repo — the planner decides the cleanest ordering that satisfies both, e.g. validate repo only in the no-`--from` branch.)
- `--rename` interaction: because reinstall dispatches and returns before the rename logic, the `--rename` guard cannot misfire on reinstall args. If BOTH `--rename` and the `reinstall` subcommand are supplied, error clearly (mutually exclusive).

**Catalog Resolution & Output (RST-02, criterion 1)**
- `--from PATH`: resolve to the explicit catalog file; error clearly if it is missing or not a regular file.
- No `--from`: invoke the existing `select_computer` (interactive picker; `--computer NAME` flows through for non-interactive selection) to choose a computer folder, then use the newest catalog in that folder by the filename timestamp (reuse the existing timestamp-from-filename logic the retention/naming layer already uses — NOT mtime).
- Output: write `reinstall.sh` to the current working directory, mode 0o644 (not executable), print its absolute path to stdout, exit 0. Overwrite an existing `reinstall.sh` (idempotent regeneration). The emitter/CLI NEVER subprocess-runs the script.
- Provenance values to the emitter: `source_name` = the catalog file's basename; `generated` = the current date as `YYYY-MM-DD` (consistent with catalog naming).

**Module Wiring & Integration Test (criterion 3/4)**
- New `src/maccat/reinstall/picker.py::resolve_catalog_path(...)` — encapsulates the `--from` vs picker resolution and the newest-by-filename-timestamp selection.
- New `src/maccat/reinstall/cli.py::run_reinstall(args, ...)` — orchestrates `resolve_catalog_path` → `parse_catalog` (Phase 24) → `emit_reinstall_script` (Phase 25) → write the file at 0o644 → print absolute path. Root `cli.py` only imports `run_reinstall` and dispatches (keeps root `cli.py` minimal; deferred import per PKG-03).
- Pipeline: `parse_catalog(path)` → `emit_reinstall_script(catalog, source_name=..., generated=...)` → write string at 0o644.
- Protect the 13-step path (criterion 3): the reinstall branch is an early `return`; make ZERO edits to existing gen-path code beyond adding the dispatch branch + subparser. Add a regression assertion that a non-reinstall invocation still runs the gen path.
- Integration test (criterion 4): drive the CLI in-process (call `run()` with patched `sys.argv`/args in a temp cwd) with `--from <fixture catalog>`; assert `reinstall.sh` exists, is mode 0o644, contains the expected shebang (`#!/usr/bin/env bash`) and provenance header, the process exits 0, and the `--rename` guard does not fire. (subprocess-against-pyz is the heavier alternative; in-process is the chosen approach.)

### Claude's Discretion
- Exact `resolve_catalog_path` / `run_reinstall` signatures, the precise ordering that lets `--from` skip repo validation while the picker path enforces it, fixture-catalog content, and test-helper structure are at Claude's discretion within these decisions.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. (Diffing DIFF-01, more browsers BRW-01, pipx/PyPI PKG-04, brew taps RST-03, and AI-CLI auto-restore RST-04 are all v2 per REQUIREMENTS.md. This phase closes the v2.1.0 milestone.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RST-01 | `maccat reinstall` generates a `reinstall.sh` from a catalog, prints its output path, and never auto-executes it; the file is written non-executable (mode 0644). | `emit_reinstall_script` returns a complete string; `os.chmod(path, 0o644)` after `Path.write_text`; `Path.resolve()` for absolute path print. |
| RST-02 | `--from PATH` selects an explicit catalog file; if omitted, the existing interactive computer-picker selects a computer and uses that computer's newest catalog (reuses `select_computer` + catalog-dir resolution; the parent `--computer` flag flows through). | `select_computer(catalog_repo, computer_name=...)` and `resolve_computer_selection(computer=...)` are the exact APIs to reuse; `parse_catalog_filename` + max-by-timestamp implements "newest catalog" without mtime. |
</phase_requirements>

## Summary

Phase 26 closes the v2.1.0 milestone by wiring the Phase 24 parser and Phase 25 emitter into a live CLI subcommand. The work is three surgical additions: (1) a `reinstall` subparser added to `_build_parser()`, (2) a one-liner dispatch branch inserted into `run()` at a precise location, and (3) two new modules (`reinstall/picker.py`, `reinstall/cli.py`) that contain all the new logic. The existing 13-step catalog-gen path in `cli.py` must not change at all beyond those additions.

The main design tension is the catalog-repo validation ordering: `validate_catalog_repo` currently runs unconditionally at step 4 and raises `SystemExit` when the repo is absent or not a git repo. The `--from` path has no need of a catalog repo at all, so the dispatch must happen before or conditionally around the validation call. The cleanest resolution — confirmed from reading the actual code — is to dispatch the `--from`-mode reinstall branch immediately after `resolve_catalog_repo` completes but BEFORE `validate_catalog_repo` runs; then call `validate_catalog_repo` and proceed with either the picker-mode reinstall or the gen-path. This splits step 4 into two sub-steps and keeps the `--from` path repo-agnostic.

The integration test drives `run()` in-process using `monkeypatch.setattr(sys, "argv", ...)` and `monkeypatch.chdir(tmp_path)`, builds a real fixture catalog in `tmp_path`, and then asserts `reinstall.sh` exists with mode 0o644, the correct shebang, and a provenance header — exactly mirroring the existing `test_cli.py` style.

**Primary recommendation:** Insert the reinstall dispatch at two points — an early-exit for `--from` mode (before `validate_catalog_repo`) and a second exit for picker mode (after `validate_catalog_repo`, before the `--rename` short-circuit). Both branches return, so the 13-step gen path is fully protected.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CLI surface (subparser, flags) | `src/maccat/cli.py` | — | All argparse lives in `_build_parser()`; no other file adds to the parser |
| `--from` vs picker resolution | `src/maccat/reinstall/picker.py` | `src/maccat/identity.py` (select_computer) | Encapsulates both branches; delegates picker to identity.py |
| Newest-catalog selection | `src/maccat/reinstall/picker.py` | `src/maccat/naming.py` (parse_catalog_filename) | Reuses naming timestamp logic; no new glob logic needed |
| Orchestration (parse → emit → write) | `src/maccat/reinstall/cli.py` | — | run_reinstall owns the pipeline sequence |
| Script generation | `src/maccat/reinstall/emitter.py` (Phase 25) | `src/maccat/reinstall/parser.py` (Phase 24) | Unmodified from prior phases |
| File write + chmod + path print | `src/maccat/reinstall/cli.py` | — | Single responsibility, no subprocess |
| Dispatch (root cli.py → run_reinstall) | `src/maccat/cli.py` | `src/maccat/reinstall/cli.py` | One-liner import+call; all logic stays in reinstall/cli.py |
| Integration testing | `tests/test_cli.py` (or `tests/reinstall/test_reinstall_cli.py`) | — | In-process, mirrors existing test_cli.py style |

## Standard Stack

### Core (all stdlib — no new dependencies)
| Module | Version | Purpose |
|--------|---------|---------|
| `argparse` | stdlib | Subparser wiring for `reinstall` |
| `pathlib.Path` | stdlib | File write, mode, resolve |
| `os` | stdlib | `os.chmod(path, 0o644)` after write |
| `datetime` | stdlib | `generated` date as `YYYY-MM-DD` |

**Installation:** None — stdlib only, consistent with project constraint.

## Package Legitimacy Audit

No external packages are installed in this phase. N/A.

## Architecture Patterns

### Research Question 1: Exact `run()` Dispatch Insertion

Reading `cli.py` end-to-end (lines 108-283), the current step 4 is a single block (lines 197-201):

```python
# ------------------------------------------------------------------
# 4. Resolve catalog repo (CFG-01 chain: flag > env > config > error)
#    PKG-03: NEVER infer from __file__ or cwd
# ------------------------------------------------------------------
cfg = load_config()
catalog_repo: Path = resolve_catalog_repo(args.catalog_dir, cfg)
validate_catalog_repo(catalog_repo)

auto_commit = not args.no_commit
```

The `--rename` short-circuit sits at lines 207-210 (step 5), after `validate_catalog_repo` has already run.

**The tension:** `--from PATH` mode does NOT require a valid catalog repo. `validate_catalog_repo` (line 199) runs before any dispatch point currently exists. If the user has no catalog repo configured, `resolve_catalog_repo` (line 198) raises `SystemExit` at level 4 with "No catalog directory configured" — before any reinstall dispatch can happen.

**Recommended ordering (cleanest split of step 4):**

```python
# ------------------------------------------------------------------
# 4a. Config load (always required — load_config is safe on absent file)
# ------------------------------------------------------------------
cfg = load_config()

# ------------------------------------------------------------------
# 4b. Reinstall --from dispatch (early exit — no repo needed)
#     Must run before resolve_catalog_repo, which raises SystemExit
#     when no repo is configured. --from mode bypasses the repo entirely.
# ------------------------------------------------------------------
if args.subcommand == "reinstall" and args.from_path is not None:
    from maccat.reinstall.cli import run_reinstall
    run_reinstall(args)
    return

# ------------------------------------------------------------------
# 4c. Resolve + validate catalog repo (required for ALL remaining paths:
#     picker-mode reinstall, --rename, and catalog generation)
# ------------------------------------------------------------------
catalog_repo: Path = resolve_catalog_repo(args.catalog_dir, cfg)
validate_catalog_repo(catalog_repo)
auto_commit = not args.no_commit

# ------------------------------------------------------------------
# 4d. Reinstall picker dispatch (after repo validated — picker needs it)
#     Before --rename short-circuit (step 5).
# ------------------------------------------------------------------
if args.subcommand == "reinstall":
    from maccat.reinstall.cli import run_reinstall
    run_reinstall(args, catalog_repo=catalog_repo)
    return

# ------------------------------------------------------------------
# 5. --rename short-circuit (update-list.sh:2447-2451)
# ------------------------------------------------------------------
if args.rename:
    ...
```

This cleanly satisfies both constraints:
- `--from` mode never reaches `resolve_catalog_repo` — works with no configured repo.
- Picker mode (no `--from`) validates the repo first — select_computer needs `catalog_repo`.
- The existing `--rename` short-circuit at step 5 is UNCHANGED.
- ZERO lines of existing gen-path code (steps 6-13) are touched.

**`--rename` + `reinstall` mutual exclusion:** The `config` guard at step 2 (lines 164-166) already checks `args.rename`. The same pattern applies: add a check in the reinstall dispatch block:

```python
if args.subcommand == "reinstall":
    if args.rename:
        sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")
    ...
```

[VERIFIED: codebase read — lines 108-283 of src/maccat/cli.py]

### Research Question 2: argparse Subparser Wiring

The current parser (lines 96-105 of `cli.py`) uses:

```python
subparsers = parser.add_subparsers(dest="subcommand")
config_parser = subparsers.add_parser(
    "config",
    help="Configuration management subcommands",
)
config_sub = config_parser.add_subparsers(dest="config_subcommand")
config_sub.add_parser("init", help="Interactive first-run setup")
config_sub.add_parser("show", help="Print effective configuration")
```

Adding `reinstall` is a single `add_parser` call plus one argument:

```python
reinstall_parser = subparsers.add_parser(
    "reinstall",
    help="Generate reinstall.sh from a catalog",
)
reinstall_parser.add_argument(
    "--from",
    metavar="PATH",
    dest="from_path",
    default=None,
    help="Explicit catalog file path (skips picker)",
)
```

Note: `--from` would conflict with Python's `from` keyword if used as an `argparse` dest, so `dest="from_path"` is required. `args.from_path` is the correct attribute name.

**Top-level flags alongside subcommands:** `--computer`, `--catalog-dir`, `--rename`, `--no-commit`, `--archive-days` are all registered on the root `parser`. argparse makes these available in the same `Namespace` alongside `args.subcommand` and `args.from_path` when a subcommand is active. There is no "swallowing" issue for top-level flags registered on the parent parser — this is confirmed by the existing `config` subcommand tests (e.g., `test_config_show_rename_flag_errors` patches `["maccat", "config", "show", "--rename"]` and the resulting `Namespace` has `args.rename == True`). The `--computer` flag is thus accessible as `args.computer` inside the reinstall dispatch. [VERIFIED: codebase read — test_cli.py lines 393-411]

**Detecting the subcommand:** `args.subcommand == "reinstall"` is the detection pattern, matching the existing `if args.subcommand == "config":` at line 159.

**Gotcha — argparse does not parse `--from` literally:** The `--from` flag dest must be overridden to `from_path` because Python's `argparse` derives the dest by stripping `--` and replacing `-` with `_`, giving `from_` — but that trailing underscore is also valid. However, using `dest="from_path"` is cleaner and more readable. Either works; `from_path` is recommended.

[VERIFIED: codebase read — lines 96-105 and 159-182 of src/maccat/cli.py]

### Research Question 3: Picker Reuse — Exact Signatures

**`resolve_computer_selection`** (identity.py, lines 80-99):
```python
def resolve_computer_selection(
    *,
    computer: str | None,
) -> str | None:
```
Validates and returns the `--computer` flag value, or returns `None` for interactive fallback. Pure function, no side effects.

**`select_computer`** (identity.py, lines 260-404):
```python
def select_computer(
    catalog_repo: Path,
    *,
    computer_name: str | None = None,
) -> str | None:
```
Returns the chosen folder name (str) or `None` if the user quit. When `computer_name` is not None (flag path), runs `mkdir -p` + `upsert_machine_label` and returns. When `None` (interactive path), shows the menu.

**How `--computer` flows through:** `args.computer` (top-level flag, accessible alongside the subcommand) is passed to `resolve_computer_selection(computer=args.computer)` → result is passed to `select_computer(catalog_repo, computer_name=result)`. The existing gen-path does exactly this at steps 6 (lines 215-219). The picker module replicates this two-call pattern.

**Newest catalog by filename timestamp:** The existing `retention.py::retain_newest_per_host` implements the newest-per-host selection in its pass 1 loop. The same logic inlined for a single folder:

```python
from maccat.naming import parse_catalog_filename

def _find_newest_catalog(folder: Path) -> Path | None:
    """Return the catalog file with the lexicographically greatest timestamp, or None."""
    best_ts: str | None = None
    best_path: Path | None = None
    for f in folder.glob("mac-software-list-*.txt"):
        if not f.is_file():
            continue
        cf = parse_catalog_filename(f.name)
        if cf is None:
            continue
        if best_ts is None or cf.timestamp > best_ts:
            best_ts = cf.timestamp
            best_path = f
    return best_path
```

This directly mirrors `retention.py` pass 1 (lines 64-72) without importing retention — keeping the picker module's dependency surface minimal. The timestamp is a 14-digit YYYYMMDDHHMMSS string so lexicographic `>` comparison is correct (same as retention.py).

**Catalog filename format** (naming.py, line 19):
```
mac-software-list-[{machine}]-{timestamp}.txt
```
The `_FILENAME_RE` regex is: `r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$"`

[VERIFIED: codebase read — identity.py lines 80-99, 260-294; naming.py lines 18-71; retention.py lines 60-87]

### Research Question 4: 0o644 Write — Stdlib Idiom

The standard approach for writing a file then setting mode 0o644:

```python
import os
from pathlib import Path

output_path = Path.cwd() / "reinstall.sh"
output_path.write_text(script_content, encoding="utf-8")
os.chmod(output_path, 0o644)
print(str(output_path.resolve()))
```

`Path.write_text` creates/overwrites the file. `os.chmod` sets the mode afterward. The file is NOT made executable (0o644 = rw-r--r--). `Path.resolve()` returns the absolute path as a `Path`; `str(...)` converts to string for printing.

**Mode assertion in tests:**
```python
assert oct(output_path.stat().st_mode & 0o777) == "0o644"
```
This masks off the file-type bits (0o170000) and compares just the permission bits. The exact string is `"0o644"`.

**Overwrite behavior:** `Path.write_text` overwrites an existing file unconditionally. This satisfies the "idempotent regeneration" requirement with no additional logic.

[ASSUMED — stdlib idiom; standard Python behavior, not verified via external docs in this session]

### Research Question 5: Integration Test Structure

**Pattern from `tests/test_cli.py`:** The existing tests use:
1. `monkeypatch.setattr(sys, "argv", ["maccat", ...])` to inject argv
2. `monkeypatch.setenv("MACCAT_CATALOG_DIR", str(catalog_repo))` to inject the catalog repo
3. `monkeypatch.setattr("maccat.gitops.git_pull", MagicMock())` etc. to suppress side effects
4. Direct call to `from maccat.cli import run; run()` — in-process
5. `pytest.raises(SystemExit)` for exit-code assertions
6. `git_repo` fixture from `conftest.py` for an isolated git repo

**Recommended integration test structure for Phase 26:**

```python
class TestReinstallSubcommand:
    """Integration test for maccat reinstall."""

    @pytest.fixture()
    def fixture_catalog(self, tmp_path: Path) -> Path:
        """Write a minimal but valid catalog file to tmp_path."""
        content = (
            "Installed Mac Software List\n"
            "------------------------------------\n"
            "\n"
            "Homebrew Packages\n"
            "------------------------------------\n"
            "wget (1.21.3)\n"
            "\n"
        )
        catalog = tmp_path / "mac-software-list-[TestMac]-20260616120000.txt"
        catalog.write_text(content, encoding="utf-8")
        return catalog

    def test_from_path_writes_reinstall_sh(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fixture_catalog: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys, "argv", ["maccat", "reinstall", "--from", str(fixture_catalog)]
        )

        from maccat.cli import run
        run()

        output = tmp_path / "reinstall.sh"
        assert output.exists()
        assert oct(output.stat().st_mode & 0o777) == "0o644"
        text = output.read_text(encoding="utf-8")
        assert text.startswith("#!/usr/bin/env bash")
        assert "Generated from:" in text
        assert fixture_catalog.name in text

    def test_rename_guard_does_not_fire_on_reinstall(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fixture_catalog: Path
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys, "argv", ["maccat", "reinstall", "--from", str(fixture_catalog)]
        )
        # If --rename guard fires, it would call gitops.git_pull; assert it does not
        mock_pull = MagicMock()
        monkeypatch.setattr("maccat.gitops.git_pull", mock_pull)

        from maccat.cli import run
        run()

        mock_pull.assert_not_called()  # reinstall returns before git ops

    def test_gen_path_not_triggered_by_reinstall(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fixture_catalog: Path,
        git_repo: Path,
    ) -> None:
        """Criterion 3: no catalog .txt file written when using reinstall subcommand."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys, "argv", ["maccat", "reinstall", "--from", str(fixture_catalog)]
        )
        from maccat.cli import run
        run()

        # No mac-software-list-*.txt file should appear anywhere in tmp_path
        txt_files = list(tmp_path.glob("mac-software-list-*.txt"))
        assert len(txt_files) == 0

    def test_reinstall_rename_mutual_exclusion(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fixture_catalog: Path
    ) -> None:
        monkeypatch.setattr(
            sys, "argv",
            ["maccat", "--rename", "reinstall", "--from", str(fixture_catalog)]
        )
        from maccat.cli import run
        with pytest.raises(SystemExit) as exc:
            run()
        assert exc.value.code != 0
```

**`monkeypatch.chdir`:** pytest's `monkeypatch` provides `.chdir(path)` which changes `os.getcwd()` for the duration of the test and restores it afterward. Use this to place `Path.cwd() / "reinstall.sh"` inside `tmp_path`. [ASSUMED — standard pytest monkeypatch API]

**Exit-code 0 assertion:** `run()` returns normally (no `SystemExit`) on success. Asserting no exception is raised is sufficient. For non-zero exits, the pattern `with pytest.raises(SystemExit) as exc: ...; assert exc.value.code != 0` matches the existing style.

**`--from` path does NOT need a git repo:** Because the `--from` dispatch fires before `validate_catalog_repo`, the test does NOT need the `git_repo` fixture — `tmp_path` alone is sufficient. This simplifies the fixture setup.

[VERIFIED: codebase read — tests/test_cli.py; tests/conftest.py]

### Research Question 6: Recommended Signatures

**`reinstall/picker.py::resolve_catalog_path`:**

```python
from __future__ import annotations

import argparse
from pathlib import Path


def resolve_catalog_path(
    args: argparse.Namespace,
    catalog_repo: Path | None = None,
) -> Path:
    """Resolve the catalog file to reinstall from.

    --from PATH branch: catalog_repo is not used (may be None).
    Picker branch: catalog_repo is required (caller validates it exists).

    Returns: Path to the resolved catalog file.
    Raises: SystemExit on any resolution failure.
    """
```

Internally this function:
1. If `args.from_path` is not None: validate it is a regular file, return `Path(args.from_path).resolve()`.
2. Else (picker branch): call `resolve_computer_selection(computer=args.computer)` → `select_computer(catalog_repo, computer_name=...)` → `_find_newest_catalog(catalog_repo / computer)` → validate and return.

**`reinstall/cli.py::run_reinstall`:**

```python
from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path


def run_reinstall(
    args: argparse.Namespace,
    catalog_repo: Path | None = None,
) -> None:
    """Orchestrate reinstall.sh generation.

    Args:
        args: Parsed argparse Namespace (has .from_path, .computer).
        catalog_repo: Resolved catalog repo path, or None when --from is supplied.
    """
```

**Why pass `argparse.Namespace` rather than individual fields:** The existing `config_init()` and `config_show()` pattern in `cli.py` passes full objects (e.g. `config_show(args.catalog_dir, load_config(), None)`). Passing `args` directly to `run_reinstall` keeps the root cli.py dispatch as a single call. It also avoids re-declaring all the flag names in the function signature as the surface grows.

**Root `cli.py` dispatch (complete one-liner form):**
```python
# In the 4b block (--from mode, before validate_catalog_repo):
if args.subcommand == "reinstall" and args.from_path is not None:
    if args.rename:
        sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")
    from maccat.reinstall.cli import run_reinstall
    run_reinstall(args)
    return

# ... validate_catalog_repo(catalog_repo) ...

# In the 4d block (picker mode, after validate_catalog_repo):
if args.subcommand == "reinstall":
    if args.rename:
        sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")
    from maccat.reinstall.cli import run_reinstall
    run_reinstall(args, catalog_repo=catalog_repo)
    return
```

The deferred import `from maccat.reinstall.cli import run_reinstall` inside the conditional body satisfies PKG-03 (lazy import). The import appears twice but in practice only one branch executes per run — identical to how `rename_machine` is imported deferred inside `run()`.

[VERIFIED: codebase read — cli.py lines 129-148 (deferred import pattern), identity.py signatures]

### Research Question 7: Catalog Repo Validation Tension Resolution

**Confirmed resolution:** Split the current monolithic step 4 into sub-steps 4a/4b/4c/4d as described in Research Question 1.

The key insight from reading `config.py`:
- `load_config()` (line 67) is always safe — it returns `Config()` if the file is absent.
- `resolve_catalog_repo()` (line 97) raises `SystemExit` if no source provides a value. This is what blocks `--from` mode.
- `validate_catalog_repo()` (line 184) raises `SystemExit` if the dir doesn't exist or isn't a git repo.

The `--from` dispatch must happen BEFORE `resolve_catalog_repo` is called, otherwise a user with no catalog configured but a local catalog file they want to use would get "ERROR: No catalog directory configured" before the reinstall can dispatch.

The two-point dispatch pattern (4b for `--from`, 4d for picker) is the only approach that satisfies all constraints without restructuring the existing code. Both dispatch points early-return, so the gen path (steps 5-13) is unreachable from any reinstall invocation.

[VERIFIED: codebase read — config.py lines 97-137, 184-209; cli.py lines 197-210]

### Recommended Project Structure (new files only)

```
src/maccat/reinstall/
├── __init__.py          # existing (no change)
├── parser.py            # existing Phase 24 (no change)
├── emitter.py           # existing Phase 25 (no change)
├── picker.py            # NEW: resolve_catalog_path + _find_newest_catalog
└── cli.py               # NEW: run_reinstall

tests/reinstall/
├── __init__.py          # existing (no change)
├── test_emitter.py      # existing Phase 25 (no change)
├── test_parser_contract.py  # existing Phase 24 (no change)
└── test_reinstall_cli.py    # NEW: integration + unit tests for Phase 26

src/maccat/cli.py        # MODIFIED: +subparser, +two dispatch points (~20 lines added)
```

### Anti-Patterns to Avoid

- **Touching the gen path:** Any edit to lines 207-283 of `cli.py` (the `--rename` block through the end of `run()`) is out of scope and risks regressions. The dispatch branches return before reaching these lines.
- **`subprocess.run("./reinstall.sh")`:** Explicitly prohibited. The emitter returns a string; the CLI writes it and prints the path. Never execute it.
- **Using `mtime` for "newest catalog":** `_find_newest_catalog` must use the filename timestamp (14-digit YYYYMMDDHHMMSS from `parse_catalog_filename`), not `Path.stat().st_mtime`. File mtime can be wrong after a git clone/pull.
- **`args.from_`:** argparse would auto-derive `dest="from_"` for `--from`. Always use explicit `dest="from_path"` to avoid the trailing-underscore confusion.
- **Single dispatch point:** A single `if args.subcommand == "reinstall":` after `validate_catalog_repo` would work for picker mode but break `--from` mode when no catalog repo is configured. Two dispatch points (4b and 4d) are required.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timestamp extraction from filename | Custom regex | `parse_catalog_filename` from `maccat.naming` | Already tested and matches the exact naming convention |
| Newest file selection | Sort-by-mtime or custom logic | Inline pass-1 from `retention.py` using `parse_catalog_filename` | Matches the retention module's semantics exactly |
| Interactive computer picker | New menu/prompt code | `select_computer` + `resolve_computer_selection` from `maccat.identity` | Already handles TTY guard, saved-default, Create-new, Quit |
| Shell-value escaping in script | Custom quoting | `quote_for_script()` from `maccat.reinstall.emitter` | The emitter already handles all injection safety |
| Script generation | New template/builder | `emit_reinstall_script(catalog, source_name=..., generated=...)` from Phase 25 | Complete API, returns a string |

## Common Pitfalls

### Pitfall 1: `--from` Mode Blocked by `resolve_catalog_repo`
**What goes wrong:** Dispatch placed after `validate_catalog_repo` (or even after `resolve_catalog_repo`). User with `--from /path/to/catalog.txt` and no configured catalog repo gets "ERROR: No catalog directory configured" before reinstall runs.
**Why it happens:** The current step 4 is monolithic; `resolve_catalog_repo` raises unconditionally when no source provides a value.
**How to avoid:** Dispatch `--from` mode after `load_config()` but before `resolve_catalog_repo()`. Use the two-point dispatch pattern (4b and 4d).
**Warning signs:** Test `test_from_path_requires_no_catalog_repo` fails — running `maccat reinstall --from /tmp/catalog.txt` without `MACCAT_CATALOG_DIR` set exits with "No catalog directory configured".

### Pitfall 2: `args.from_` vs `args.from_path`
**What goes wrong:** argparse auto-derives `dest="from_"` from `--from` (strips `--`, replaces `-` with `_`, result: `from_`). Code references `args.from_path` but the actual attribute is `args.from_`.
**Why it happens:** `--from` without explicit `dest` uses `from_` — the trailing underscore is valid Python but easy to miss.
**How to avoid:** Always declare `dest="from_path"` explicitly in `reinstall_parser.add_argument("--from", dest="from_path", ...)`.
**Warning signs:** `AttributeError: Namespace object has no attribute 'from_path'` at runtime.

### Pitfall 3: Mode Bit After `write_text`
**What goes wrong:** `Path.write_text` creates the file with the default umask permissions (typically 0o644 on macOS, but not guaranteed). Relying on umask alone means the mode assertion `oct(path.stat().st_mode & 0o777) == "0o644"` may fail on machines with a restrictive umask (e.g., 0o022 gives 0o644, but 0o027 gives 0o640).
**Why it happens:** umask is process-wide and user-configurable.
**How to avoid:** Always call `os.chmod(output_path, 0o644)` explicitly after `write_text`. This is unconditional and deterministic.
**Warning signs:** Mode assertion fails on CI but passes locally.

### Pitfall 4: `from maccat.reinstall.cli import run_reinstall` Outside the `if` Block
**What goes wrong:** Importing `run_reinstall` at the top of `run()` or outside the dispatch `if` block violates PKG-03 (deferred imports). All `maccat.*` imports in `cli.py` must live inside function bodies.
**Why it happens:** Refactoring instinct puts imports at the top of the function body.
**How to avoid:** Keep the `from maccat.reinstall.cli import run_reinstall` inside the `if args.subcommand == "reinstall":` block, just as the existing `from maccat import gitops` block is inside `run()`.
**Warning signs:** `mypy --strict` or `ruff` may not catch this; it's a design constraint, not a syntax error.

### Pitfall 5: `select_computer` Returns None (User Quit) — No Catalog File
**What goes wrong:** In picker mode, `select_computer` returns `None` when the user quits the menu. If `_find_newest_catalog` is then called with `catalog_repo / None`, a `TypeError` occurs.
**Why it happens:** The existing gen-path handles this: `if computer is None: return` (lines 217-219 of `cli.py`). The reinstall picker path must replicate this guard.
**How to avoid:** In `resolve_catalog_path`, after `select_computer(...)` returns `None`, call `sys.exit(0)` (or `return None` and let the caller handle it) with "No catalog written." consistent with the existing behavior.
**Warning signs:** `TypeError: unsupported operand type(s) for /: 'Path' and 'NoneType'` on test with user-quit simulation.

### Pitfall 6: `monkeypatch.chdir` Scope
**What goes wrong:** `monkeypatch.chdir` changes `os.getcwd()` for the test. If `Path.cwd()` is called at import time or module initialization rather than inside `run_reinstall`, it captures the wrong directory.
**Why it happens:** Module-level `cwd = Path.cwd()` captures cwd at import, not at call time.
**How to avoid:** Call `Path.cwd()` inside `run_reinstall()` body, not at module level or inside `resolve_catalog_path`.
**Warning signs:** `reinstall.sh` written to the real cwd instead of `tmp_path`; integration test can't find the file.

## Code Examples

### Complete `_build_parser()` Addition
```python
# Source: codebase read — cli.py lines 96-105 (existing pattern)
# Add after the config_sub.add_parser("show", ...) line:
reinstall_parser = subparsers.add_parser(
    "reinstall",
    help="Generate reinstall.sh from a catalog",
)
reinstall_parser.add_argument(
    "--from",
    metavar="PATH",
    dest="from_path",
    default=None,
    help="Explicit catalog file path (skips computer picker)",
)
```

### `reinstall/picker.py` — Core Logic
```python
# Source: codebase read — naming.py, retention.py, identity.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from maccat.naming import parse_catalog_filename


def _find_newest_catalog(folder: Path) -> Path | None:
    """Return the catalog file with the greatest filename timestamp, or None."""
    best_ts: str | None = None
    best_path: Path | None = None
    for f in folder.glob("mac-software-list-*.txt"):
        if not f.is_file():
            continue
        cf = parse_catalog_filename(f.name)
        if cf is None:
            continue
        if best_ts is None or cf.timestamp > best_ts:
            best_ts = cf.timestamp
            best_path = f
    return best_path


def resolve_catalog_path(
    args: argparse.Namespace,
    catalog_repo: Path | None = None,
) -> Path:
    """Resolve the catalog file to use for reinstall generation."""
    if args.from_path is not None:
        p = Path(args.from_path).expanduser().resolve()
        if not p.is_file():
            sys.exit(f"ERROR: Catalog file not found or not a regular file: {p}")
        return p

    # Picker branch — catalog_repo required
    if catalog_repo is None:
        sys.exit("ERROR: catalog_repo is required for picker mode.")

    from maccat.identity import resolve_computer_selection, select_computer

    computer_pre = resolve_computer_selection(computer=args.computer)
    computer = select_computer(catalog_repo, computer_name=computer_pre)
    if computer is None:
        # User quit the picker — exit cleanly with no file written
        sys.exit(0)

    folder = catalog_repo / computer
    catalog_path = _find_newest_catalog(folder)
    if catalog_path is None:
        sys.exit(f"ERROR: No catalog files found in {folder}")
    return catalog_path
```

### `reinstall/cli.py` — Orchestration
```python
# Source: codebase read — emitter.py, parser.py, cli.py conventions
from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path


def run_reinstall(
    args: argparse.Namespace,
    catalog_repo: Path | None = None,
) -> None:
    """Generate reinstall.sh and write it to the current working directory."""
    from maccat.reinstall.cli_helpers import resolve_catalog_path  # or picker
    from maccat.reinstall.emitter import emit_reinstall_script
    from maccat.reinstall.parser import parse_catalog

    catalog_path = resolve_catalog_path(args, catalog_repo=catalog_repo)
    catalog = parse_catalog(catalog_path)
    script = emit_reinstall_script(
        catalog,
        source_name=catalog_path.name,
        generated=date.today().strftime("%Y-%m-%d"),
    )

    output_path = Path.cwd() / "reinstall.sh"
    output_path.write_text(script, encoding="utf-8")
    os.chmod(output_path, 0o644)
    print(str(output_path.resolve()))
```

### Mode Assertion (tests)
```python
# Source: CONTEXT.md specifics section
assert oct(output_path.stat().st_mode & 0o777) == "0o644"
```

### `root cli.py` Two-Point Dispatch (complete block)
```python
# Source: codebase read — cli.py lines 196-210
# REPLACES the current monolithic step 4:

cfg = load_config()
catalog_repo: Path = resolve_catalog_repo(args.catalog_dir, cfg)

# ------------------------------------------------------------------
# 4b. Reinstall --from dispatch (early exit — no repo validation needed)
# ------------------------------------------------------------------
if args.subcommand == "reinstall" and args.from_path is not None:
    if args.rename:
        sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")
    from maccat.reinstall.cli import run_reinstall
    run_reinstall(args)
    return

validate_catalog_repo(catalog_repo)
auto_commit = not args.no_commit

# ------------------------------------------------------------------
# 4d. Reinstall picker dispatch (repo validated — picker needs it)
# ------------------------------------------------------------------
if args.subcommand == "reinstall":
    if args.rename:
        sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")
    from maccat.reinstall.cli import run_reinstall
    run_reinstall(args, catalog_repo=catalog_repo)
    return

# ------------------------------------------------------------------
# 5. --rename short-circuit (UNCHANGED)
# ------------------------------------------------------------------
if args.rename:
    ...
```

Note: this still calls `resolve_catalog_repo` before the `--from` dispatch. If the user has no catalog configured AND uses `--from`, `resolve_catalog_repo` will raise. To fully isolate `--from` from the repo, the `--from` dispatch must happen before `resolve_catalog_repo` too. The cleanest fully-isolated version:

```python
cfg = load_config()

# 4b. --from mode: no repo needed at all
if args.subcommand == "reinstall" and args.from_path is not None:
    if args.rename:
        sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")
    from maccat.reinstall.cli import run_reinstall
    run_reinstall(args)
    return

# 4c. Resolve + validate repo (all remaining paths need it)
catalog_repo: Path = resolve_catalog_repo(args.catalog_dir, cfg)
validate_catalog_repo(catalog_repo)
auto_commit = not args.no_commit

# 4d. Picker-mode reinstall
if args.subcommand == "reinstall":
    if args.rename:
        sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")
    from maccat.reinstall.cli import run_reinstall
    run_reinstall(args, catalog_repo=catalog_repo)
    return

# 5. --rename short-circuit (UNCHANGED from current line 207)
if args.rename:
    ...
```

This is the recommended final form. `resolve_catalog_repo` is now called only in the 4c block for paths that actually need a repo.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `Path.write_text` creates/overwrites unconditionally | Research Q4 | Overwrite behavior could differ; test would catch this immediately |
| A2 | `os.chmod(path, 0o644)` after `write_text` gives deterministic permissions | Research Q4 | Mode assertion in tests catches any deviation |
| A3 | `monkeypatch.chdir` is available in the pytest version used by this project | Research Q5 | pytest 3.9+ provides it; standard pytest API |

**All three are low-risk stdlib/pytest behaviors confirmed by general knowledge.**

## Open Questions

1. **`--rename` + `reinstall` mutual exclusion placement:**
   The `--rename` guard check can be centralized (once at the top of the reinstall branch) or duplicated in both 4b and 4d blocks. Centralizing at 4b would miss the case where `--rename` is passed with picker-mode reinstall (no `--from`). The per-block approach (as shown in the code examples) is recommended — each dispatch point independently checks and rejects the combination.

2. **`sys.exit(0)` vs `return None` for picker-quit in `resolve_catalog_path`:**
   Two options: (a) `resolve_catalog_path` calls `sys.exit(0)` directly (prints "No catalog written." before exiting); (b) returns `None` and the caller handles it. Option (a) matches how `select_computer` itself handles the quit case (prints "No catalog written." and returns None, but the cli.py gen-path has an explicit `if computer is None: return`). Option (b) is cleaner for testability — the test can assert `run_reinstall` returns normally without catching a `SystemExit`. Recommendation: `resolve_catalog_path` returns `None` on picker quit; `run_reinstall` checks for `None` and returns cleanly (matching the existing gen-path pattern at cli.py lines 217-219).

## Environment Availability

Step 2.6: SKIPPED — this phase is code/config-only changes. No external tools, services, or CLIs are installed. The only tools needed (`python`, `pytest`) are verified already present in the project venv.

## Validation Architecture

`workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`. Section skipped per config.

## Security Domain

This phase writes a Zsh/bash script file to disk and prints its path. The script content comes entirely from `emit_reinstall_script` (Phase 25), which already applies `shlex.quote()` via `quote_for_script()` to all catalog-derived values in command position, and `safe_comment_value()` for comment context. No new injection surface is introduced. No ASVS categories beyond V5 (input validation) apply; the existing emitter design satisfies V5.

The file is written mode 0o644 (not executable) — the user must explicitly chmod and run it. This is the required behavior per RST-01 and REQUIREMENTS.md "out of scope" table ("Auto-executing the generated script").

## Sources

### Primary (HIGH confidence — codebase read)
- `src/maccat/cli.py` lines 1-283 — `_build_parser()` and `run()` complete implementation
- `src/maccat/identity.py` lines 80-99, 260-404 — `resolve_computer_selection`, `select_computer` signatures
- `src/maccat/config.py` lines 67-137, 184-209 — `load_config`, `resolve_catalog_repo`, `validate_catalog_repo`
- `src/maccat/naming.py` lines 18-71 — filename regex, `parse_catalog_filename`, `make_catalog_filename`
- `src/maccat/retention.py` lines 37-87 — `retain_newest_per_host` pass-1 algorithm
- `src/maccat/reinstall/parser.py` lines 134-234 — `parse_catalog` signature and semantics
- `src/maccat/reinstall/emitter.py` lines 243-297 — `emit_reinstall_script` signature and contract
- `tests/test_cli.py` lines 1-473 — test style, fixtures, patching patterns
- `tests/conftest.py` lines 1-55 — `git_repo`, `catalog_repo`, `tmp_json` fixtures
- `.planning/config.json` — `nyquist_validation: false` confirmed

### Secondary (MEDIUM confidence — language/stdlib spec)
- Python stdlib `os.chmod`, `pathlib.Path.write_text`, `Path.resolve` — standard behavior
- pytest `monkeypatch.chdir` — standard pytest API (3.9+)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, no new deps
- Architecture: HIGH — read actual code; insertion points are exact line numbers
- Pitfalls: HIGH — derived from reading real code, not hypothetical
- Test patterns: HIGH — mirrored from existing test_cli.py

**Research date:** 2026-06-16
**Valid until:** 2026-07-16 (stable codebase, no external deps)
