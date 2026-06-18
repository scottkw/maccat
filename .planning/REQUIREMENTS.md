# Requirements: maccat — v3.0.0 Markdown Catalog Format

**Defined:** 2026-06-18
**Core Value:** A single run produces one complete, restorable snapshot of a machine's software *and*
tooling extensions — accurate enough to rebuild the environment from, degrading gracefully when any
source isn't installed.

## v1 Requirements

Requirements for this milestone (v3.0.0). Each maps to exactly one roadmap phase.

### Markdown Catalog Output

- [ ] **MD-01**: Catalog generation writes a markdown file with a `.md` extension; the per-machine
  filename pattern becomes `mac-software-list-[computer]-YYYYMMDDHHMMSS.md`.
- [ ] **MD-02**: Each catalog opens with a YAML frontmatter block carrying provenance — computer
  (folder), hostname, generated timestamp, and maccat version — followed by a top-level `#` title.
- [ ] **MD-03**: Every catalog source renders as a `##` section heading containing a uniform
  three-column markdown table (`Name | Version | ID`); a missing version or ID renders as an empty cell.
- [ ] **MD-04**: A source with no items renders a clear `(none found)` indicator under its heading —
  graceful degradation is preserved across the format change.
- [ ] **MD-05**: Markdown output is deterministic and stably sorted (repeated runs diff-empty) and
  never contains secrets — MCP / AI-CLI entries remain identity-only (FMT-01 / FMT-03 / FMT-04 upheld).

### `.md` Plumbing (retention / filename / git)

- [ ] **FILE-01**: Newest-per-computer retention and age-based archive pruning operate on `.md`
  catalogs (the `.txt` glob is replaced, not duplicated).
- [ ] **FILE-02**: The git pull → generate → commit/push cycle stages `.md` catalogs so additions,
  archive moves, and deletions sync in one commit; `--no-commit` still skips git.

### Convert Command

- [ ] **CONV-01**: `maccat convert --from PATH` reads a legacy plain-text `.txt` catalog (via the
  existing text parser) and rewrites its full contents — every section and every item's name /
  version / ID — as the new markdown `.md` catalog.
- [ ] **CONV-02**: convert replaces the original in place — it writes the `.md`, removes the old
  `.txt`, and stages both changes in a single commit; `--no-commit` performs the file operations
  without git.
- [ ] **CONV-03**: convert degrades gracefully on malformed or partial legacy input — it warns and
  skips unparseable content rather than aborting or fabricating data, and never executes anything.

### Markdown Reinstall

- [ ] **RIN-01**: `reinstall/parser.py` parses the new markdown catalog format (frontmatter +
  per-section tables) into the typed `ParsedCatalog`, with the parser ↔ emitter round-trip re-locked
  by the contract test against the markdown emitter.
- [ ] **RIN-02**: `maccat reinstall` consumes the markdown format only; handed a legacy `.txt`
  catalog it fails with a clear message directing the user to `convert` it first (no silent partial parse).

## v2 Requirements

Deferred to a future milestone. Tracked but not in this roadmap.

### Future Catalog / Restore

- **DIFF-01**: Catalog diffing / change reports — diff snapshots over time ("what changed since last run").
- **CONV-bulk**: Bulk conversion (`--computer NAME` / all catalogs, main + archive) — this milestone
  ships single-file `--from PATH` only.
- **PKG-04**: pipx / PyPI as a second distribution channel.
- **RST-03**: Capture & restore Homebrew taps in the reinstall flow.
- **RST-04**: Best-effort AI-CLI tooling restore (beyond the manual checklist).
- **SAF-02**: Safari content blockers (`com.apple.Safari.content-blocker`).
- Browser extension enabled/disabled state (CHR-02 / FF-02 / Edge / Brave).

## Out of Scope

Explicitly excluded for v3.0.0. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Bulk / folder-wide convert | Single-file `convert --from PATH` is the chosen surface; bulk is deferred (CONV-bulk) |
| Dual-format reinstall (read both `.txt` and `.md`) | Reinstall is markdown-only by decision; legacy catalogs are upgraded via `convert` first |
| Per-source variable table columns | Uniform 3-column `Name \| Version \| ID` table chosen for parseability and round-trip safety |
| JSON / HTML output formats | One restorable snapshot format; markdown is now that single format |
| Changing what data is collected (new sources/fields) | This milestone is format-only — the 22 sections and their data are unchanged |
| Cross-platform support | Tool remains macOS-only by design |

## Traceability

Mapped during roadmap creation (Phases 30-32; coarse granularity).

| Requirement | Phase | Status |
|-------------|-------|--------|
| MD-01 | Phase 30 | Pending |
| MD-02 | Phase 30 | Pending |
| MD-03 | Phase 30 | Pending |
| MD-04 | Phase 30 | Pending |
| MD-05 | Phase 30 | Pending |
| FILE-01 | Phase 30 | Pending |
| FILE-02 | Phase 30 | Pending |
| RIN-01 | Phase 31 | Pending |
| RIN-02 | Phase 31 | Pending |
| CONV-01 | Phase 32 | Pending |
| CONV-02 | Phase 32 | Pending |
| CONV-03 | Phase 32 | Pending |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12 (Phase 30: 7, Phase 31: 2, Phase 32: 3)
- Unmapped: 0 ✓ — 100% coverage, no orphans, no duplicates

---
*Requirements defined: 2026-06-18*
*Last updated: 2026-06-18 — traceability populated by roadmapper (Phases 30-32)*
