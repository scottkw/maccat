# Phase 26: Picker + CLI Wiring + Integration - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Make `maccat reinstall` a working subcommand: resolve a catalog (explicit `--from PATH` or
the interactive computer-picker), parse it (Phase 24), render `reinstall.sh` (Phase 25),
write the file at mode 0o644 to the current directory, print its absolute path, exit 0 —
and never subprocess-run it. Covers RST-01, RST-02.

New modules: `src/maccat/reinstall/picker.py` (`resolve_catalog_path`) and
`src/maccat/reinstall/cli.py` (`run_reinstall`). Root `src/maccat/cli.py` gains the
`reinstall` subparser + a one-liner dispatch. Plus an integration test.

Out of boundary: changing the catalog-gen pipeline, the emitter (Phase 25), or the parser
(Phase 24). The non-negotiable 13-step `cli.py run()` path MUST remain byte-behavior
identical for non-reinstall invocations.
</domain>

<decisions>
## Implementation Decisions

### CLI Surface & Dispatch Point (RST-01/02)
- Expose reinstall as a **`reinstall` subparser** (sibling to `config`, `dest="subcommand"`)
  with a `--from PATH` argument. NOT a top-level flag.
- **Dispatch point in `run()`:** after `load_config` → `resolve_catalog_repo` →
  `validate_catalog_repo`, and **before** the `--rename` short-circuit. The reinstall branch
  does its work and **returns** — it never falls through into the 13-step catalog-gen path.
- **Catalog repo requirement:** `--from PATH` is standalone and works against any catalog
  file WITHOUT requiring the configured catalog repo. Without `--from`, the repo IS required
  (the picker needs it). (Implication: if reinstall runs before `validate_catalog_repo` would
  reject a missing repo, ensure `--from` mode does not error on an absent/invalid repo — the
  planner decides the cleanest ordering that satisfies both, e.g. validate repo only in the
  no-`--from` branch.)
- **`--rename` interaction:** because reinstall dispatches and returns before the rename
  logic, the `--rename` guard cannot misfire on reinstall args. If BOTH `--rename` and the
  `reinstall` subcommand are supplied, error clearly (mutually exclusive).

### Catalog Resolution & Output (RST-02, criterion 1)
- **`--from PATH`:** resolve to the explicit catalog file; error clearly if it is missing or
  not a regular file.
- **No `--from`:** invoke the existing `select_computer` (interactive picker; `--computer
  NAME` flows through for non-interactive selection) to choose a computer folder, then use
  the **newest catalog in that folder by the filename timestamp** (reuse the existing
  timestamp-from-filename logic the retention/naming layer already uses — NOT mtime).
- **Output:** write `reinstall.sh` to the **current working directory**, mode **0o644**
  (not executable), print its **absolute path** to stdout, exit 0. **Overwrite** an existing
  `reinstall.sh` (idempotent regeneration). The emitter/CLI NEVER subprocess-runs the script.
- **Provenance values to the emitter:** `source_name` = the catalog file's basename;
  `generated` = the current date as `YYYY-MM-DD` (consistent with catalog naming).

### Module Wiring & Integration Test (criterion 3/4)
- New `src/maccat/reinstall/picker.py::resolve_catalog_path(...)` — encapsulates the
  `--from` vs picker resolution and the newest-by-filename-timestamp selection.
- New `src/maccat/reinstall/cli.py::run_reinstall(args, ...)` — orchestrates
  `resolve_catalog_path` → `parse_catalog` (Phase 24) → `emit_reinstall_script` (Phase 25) →
  write the file at 0o644 → print absolute path. Root `cli.py` only imports `run_reinstall`
  and dispatches (keeps root `cli.py` minimal; deferred import per PKG-03).
- **Pipeline:** `parse_catalog(path)` → `emit_reinstall_script(catalog, source_name=...,
  generated=...)` → write string at 0o644.
- **Protect the 13-step path (criterion 3):** the reinstall branch is an early `return`;
  make ZERO edits to existing gen-path code beyond adding the dispatch branch + subparser.
  Add a regression assertion that a non-reinstall invocation still runs the gen path.
- **Integration test (criterion 4):** drive the CLI **in-process** (call `run()` with patched
  `sys.argv`/args in a temp cwd) with `--from <fixture catalog>`; assert `reinstall.sh`
  exists, is mode 0o644, contains the expected shebang (`#!/usr/bin/env bash`) and provenance
  header, the process exits 0, and the `--rename` guard does not fire. (subprocess-against-pyz
  is the heavier alternative; in-process is the chosen approach.)

### Claude's Discretion
- Exact `resolve_catalog_path` / `run_reinstall` signatures, the precise ordering that lets
  `--from` skip repo validation while the picker path enforces it, fixture-catalog content,
  and test-helper structure are at Claude's discretion within these decisions.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/maccat/cli.py` — `_build_parser()` (argparse with a `config` subparser, `dest="subcommand"`)
  and `run()` (the 13-step orchestration: parse → config dispatch → guards → load_config →
  resolve_catalog_repo → validate_catalog_repo → `--rename` short-circuit → select_computer →
  … → git_commit_and_push). Deferred imports of all `maccat.*` modules inside `run()` (PKG-03).
- `src/maccat/identity.py::select_computer(catalog_repo, computer_name=...)` and
  `resolve_computer_selection(computer=...)` — the existing interactive picker + `--computer`
  resolution to reuse for the no-`--from` path.
- `src/maccat/config.py` — `load_config`, `resolve_catalog_repo`, `validate_catalog_repo`.
- `src/maccat/naming.py` / `src/maccat/retention.py` — existing timestamp-from-filename logic
  for "newest per host/folder" (reuse for newest-catalog selection).
- `src/maccat/reinstall/parser.py::parse_catalog(path) -> ParsedCatalog` (Phase 24).
- `src/maccat/reinstall/emitter.py::emit_reinstall_script(catalog, *, source_name, generated) -> str` (Phase 25).

### Established Patterns
- `from __future__ import annotations` line 1; deferred `maccat.*` imports inside `run()`;
  stdlib-only; ruff + mypy --strict clean; type hints; argparse subparsers via `add_parser`.
- Tests under `tests/` mirroring `src/`; `tests/test_cli.py` already exercises `run()` with
  patched argv and the `config` subcommand + `--rename`/`--computer` guards — mirror its style.

### Integration Points
- Root `cli.py` `_build_parser()` gains a `reinstall` subparser (`dest="subcommand" == "reinstall"`,
  `--from` arg). `run()` gains one dispatch branch calling `run_reinstall(args, ...)`.
- The reinstall flow consumes Phase 24 + Phase 25 public APIs and writes a 0o644 file.
</code_context>

<specifics>
## Specific Ideas

- Use a committed fixture catalog (or build one in a tmp dir) for the integration test so it
  does not depend on the user's real catalog data.
- Mode assertion: `oct(path.stat().st_mode & 0o777) == "0o644"`.
- The integration test must assert the existing gen path is NOT triggered by a reinstall
  invocation (e.g. no catalog file is written into the catalog repo, git is not invoked) —
  proving criterion 3 / the early-return.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Diffing DIFF-01, more browsers BRW-01,
pipx/PyPI PKG-04, brew taps RST-03, and AI-CLI auto-restore RST-04 are all v2 per
REQUIREMENTS.md. This phase closes the v2.1.0 milestone.)
</deferred>
