# Phase 22: Versioned Catalog - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning
**Mode:** Smart discuss — output-behavior phase (grey areas resolved with user)

<domain>
## Phase Boundary

Every software section that currently lacks a version gains one where obtainable:
Homebrew formulae, Homebrew casks, Setapp apps, and web-installed `/Applications`
apps. Each emits `name (version)` lines. Runs stay deterministic (two consecutive
runs diff-empty) and degrade gracefully (name-only) when a version can't be read.
The App Store (`mas`) section already carries versions and is left untouched.

Covers: VER-01 (formulae), VER-02 (casks), VER-03 (Setapp), VER-04 (web-installed),
VER-05 (graceful degradation), VER-06 (determinism).
</domain>

<decisions>
## Implementation Decisions

### Version output format
- Use `name (version)` — matches the catalog's existing `emit_item` convention
  (FMT-01) and the App Store section. Consistent across the whole catalog.
- Homebrew: switch `brew list --formula` → `brew list --formula --versions` and
  `brew list --cask` → `brew list --cask --versions`. `brew --versions` emits
  `name version [version2 ...]`.
- **Multiple installed versions:** show ALL versions inside the parens, space-joined,
  in the order brew reports them — e.g. `python@3.11 (3.11.1 3.11.2)`. Most faithful
  for restore. Do NOT collapse to highest-only.

### .app version extraction (Setapp + /Applications)
- Read the version from each app bundle's `Contents/Info.plist` using stdlib
  `plistlib` (handles both XML and binary plists).
- Key precedence: `CFBundleShortVersionString` first; fall back to `CFBundleVersion`;
  if neither present (or no Info.plist, or unreadable), emit the app name only.
- Setapp's container dir (`Setapp`) and `/Applications`'s own basename entry
  (`Applications`) are not apps — they have no Info.plist and must degrade to
  name-only without error (they are part of the current `find`-parity output).

### Graceful degradation (VER-05)
- Any item whose version can't be determined still appears (name only). A missing
  version, missing/zero-byte/binary-unparseable plist, or a `brew --versions` line
  with no version field must NEVER crash the run or abort the section.

### Ordering & determinism (VER-06)
- Keep each section's current ordering — `brew list` is already alphabetically
  sorted and deterministic; Setapp/web-installed already sort their entries. Adding
  a version suffix does not change ordering. Do NOT re-route these raw sections
  through `flush_section`. Two consecutive runs must remain byte-identical.

### zsh_parity tests for the changed sections (keep Phase 22's gate green honestly)
- Phase 22's output for Homebrew / Setapp / web-installed now intentionally diverges
  from the frozen `update-list.sh`, so the `zsh_parity` golden cases for those three
  sections WILL fail. They cannot be kept green truthfully (the zsh reference is NOT
  being updated — it is deleted in Phase 23).
- **Do NOT regenerate the goldens from Python's own output** — that recreates the
  tautological-parity anti-pattern caught in v1.0.0 (a parity test that asserts Python
  == Python proves nothing).
- Instead, in Phase 22, **skip** (`pytest.mark.skip` / `xfail` with a clear reason
  string referencing ZSH-02 / Phase 23) ONLY the parity cases covering the three
  changed sections, so the suite stays green and honest. Leave the App Store and the
  other unchanged parity cases intact.
- Removing `update-list.sh`, deleting the entire `zsh_parity` suite (including these
  skipped cases), dropping the CI `zsh -n` gate, and backfilling direct collector
  tests for the new versioned behavior is **Phase 23's** job (ZSH-01..04) — not this
  phase. Phase 22 only neutralizes the cases its own output change invalidates.

### Claude's Discretion
- Whether to add a small shared `Info.plist` version helper (e.g. in
  `src/maccat/helpers/`) reused by both Setapp and web-installed collectors, vs
  inline per collector — Claude's call; a shared helper is preferred to avoid
  duplication (DRY) given two collectors need identical logic.
- Exact parsing of `brew --versions` lines (split on whitespace: first token = name,
  remaining tokens = versions) — Claude's call provided multi-version output is
  preserved as decided above.
- These four collectors are currently `raw=True` (write verbatim, no `emit_item`).
  Claude may format `name (version)` manually OR reuse `emit_item(name, version, "")`
  for the paren formatting, as long as ordering is preserved (i.e. NOT via
  `flush_section`, which re-sorts) and output stays byte-deterministic.
</decisions>

<code_context>
## Existing Code Insights

### Reusable assets
- `src/maccat/catalog/format.py`:
  - `emit_item(name, version, id_)` → produces `name (version)` for `id_=""`. Can be
    reused for the paren formatting (it does NOT sort).
  - `flush_section(lines)` → `LC_ALL=C sort -f -u`. **Do NOT use** for these sections
    (would re-sort; decision is to preserve current ordering).
  - `version_sort_tail(candidates)` → highest version via `sort -V`. NOT needed given
    the "show all versions" decision (kept for Chrome).
- No existing `plistlib`/Info.plist helper anywhere in `src/` — a new one is needed
  (stdlib `plistlib`, `plistlib.load(open(path,'rb'))` handles XML + binary).

### Collectors to modify (all currently `raw=True`, write verbatim)
- `src/maccat/collectors/homebrew.py` — `_run(["brew","list","--formula"])` /
  `--cask`; concatenates `formulae + casks`. Add `--versions`; parse `name version...`.
- `src/maccat/collectors/setapp.py` — scans `/Applications/Setapp/`, prepends
  `Setapp` basename, sorts. Add per-app Info.plist version lookup.
- `src/maccat/collectors/webapps.py` — scans `/Applications/`, excludes `Setapp*` and
  `*App Store*`, prepends `Applications` basename, sorts. Add Info.plist version lookup.
- `src/maccat/collectors/mas.py` — already emits `AppName (version)`. LEAVE UNCHANGED.

### Established patterns
- stdlib-only, ruff + `mypy --strict` clean, pytest. `subprocess.run(..., shell=False)`.
- Collectors return `CollectorResult(sections=[Section(title, items, raw=True)])`.
- `available()` guards (e.g. `shutil.which("brew")`, `BASE.is_dir()`) — keep them.
</code_context>

<specifics>
## Specific Ideas

User's motivation: a catalog is a restore source — pinning versions makes it
accurate enough to rebuild from. The App Store section already shows versions; this
phase closes the gap for the four sources that don't.
</specifics>

<deferred>
## Deferred Ideas

- Versions for the extension/MCP/plugin sections — already emit `name (version) [id]`
  where obtainable; not in scope.
- Re-deriving a version when neither the CLI nor the plist provides one — out of
  scope; name-only degradation is sufficient.
- Retiring update-list.sh / parity tests — that's Phase 23. (Note for planner:
  Phase 22's output changes WILL break the zsh_parity golden files; that is expected
  and is handled in Phase 23, not here. Do not try to keep parity green.)
</deferred>
