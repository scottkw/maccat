# Phase 21: CLI Cleanup - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning
**Mode:** Smart discuss — infrastructure/refactor phase (decisions locked during milestone questioning)

<domain>
## Phase Boundary

`--computer NAME` becomes the sole named-folder selecting flag. `--personal`, `--office`,
and `--machine` are removed entirely from the codebase — parser definitions, the
mutual-exclusion group, the `resolve_computer_selection` signature/logic, and all
doc-comment examples — with no dead code paths left behind. The interactive
`select_computer` menu and the other flags (`--rename`, `--no-commit`, `--archive-days`,
`--catalog-dir`) are unchanged. Tests referencing the removed flags are updated.

Covers: CLI-03, CLI-04, CLI-05, CLI-06.
</domain>

<decisions>
## Implementation Decisions

### Flag surface (locked during milestone questioning)
- Keep `--computer NAME` as the single named-folder selector. Remove `--personal`,
  `--office`, and `--machine` completely — no hidden/deprecated aliases.
- A removed flag must produce a standard argparse "unrecognized arguments" error
  (no custom handling, no migration shim).
- `--help` must list only `--computer` for folder selection; scrub the removed flags
  from help text and from doc-comment usage examples (`cli.py` module docstring,
  `gitops.py`/`retention.py`/`writer.py`/`naming.py` example strings).

### resolve_computer_selection
- Simplify the signature to drop the `personal`, `office`, and `machine` parameters —
  it collapses to resolving `--computer` (validate name, return it) or `None` for the
  interactive fallback. Remove the four-way mutual-exclusion guard (only one flag
  remains, so argparse's group is no longer needed for these).
- Keep the `--rename` × selecting-flag guard semantics, now reduced to `--rename` ×
  `--computer`.

### Claude's Discretion
- Exact post-refactor shape of `resolve_computer_selection` (keep the function vs inline
  it) and whether the argparse mutually-exclusive group is removed or kept with a single
  member — Claude's call, provided behavior matches the decisions above and tests pass.
- Whether to keep `CURRENT_MACHINE`/`OUTPUT_FILENAME` wiring exactly as-is (it should be
  unaffected — folder name still flows through unchanged).
</decisions>

<code_context>
## Existing Code Insights

### Blast radius (files referencing the removed flags)
- `src/maccat/cli.py` — argparse mutually-exclusive group (lines ~66–92: `--personal`,
  `--office`, `--computer`, `--machine`); two guard messages (config-subcommand guard
  ~line 188, `--rename` × selecting-flag guard ~line 212); the
  `resolve_computer_selection(...)` call (~line 240) passing `personal=`/`office=`/
  `machine=`; the module docstring flag list.
- `src/maccat/identity.py` — `resolve_computer_selection` (def ~line 81) with its
  `personal`/`office`/`machine` params, the count logic, the mutual-exclusion `SystemExit`,
  and the `personal→"personal"`/`office→"office"` literal returns (~lines 103–131).
- Doc-comment-only references (no logic): `src/maccat/gitops.py:102`,
  `src/maccat/retention.py:56`, `src/maccat/catalog/writer.py:25`, `src/maccat/naming.py:69`
  — these use "personal"/"office" only as illustrative folder-name examples and can stay
  as generic examples or be reworded; not functional.

### Tests to update
- `tests/test_cli.py`, `tests/test_identity.py`, `tests/test_naming.py` reference the
  removed flags / the old `resolve_computer_selection` signature. `test_identity.py` has
  ~11 calls to `resolve_computer_selection` (lines ~97–163) that must move to the new
  signature; add coverage asserting removed flags now error.

### Established patterns
- stdlib-only, ruff + `mypy --strict` clean, pytest. Keep type hints exact (the function
  signature change must stay typed). Mirror existing argparse/test style.
</code_context>

<specifics>
## Specific Ideas

`--personal`/`--office` were one user's catalog folder names and `--machine` was a pure
back-compat alias of `--computer` — supplying the folder name via `--computer` is fully
sufficient. This is the motivation for the removal.
</specifics>

<deferred>
## Deferred Ideas

None — phase stayed within scope. (Versioned output is Phase 22; zsh retirement is Phase 23.)
</deferred>
