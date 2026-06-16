# Requirements: maccat — v2.0.0 Standalone maccat — CLI Cleanup & Versioned Catalog

**Defined:** 2026-06-16
**Core Value:** A single run produces one complete, restorable snapshot of a machine's software *and* tooling extensions — accurate enough to rebuild the environment from, degrading gracefully when any source isn't installed.

## v1 Requirements

Requirements for this milestone (v2.0.0). Each maps to a roadmap phase.

### CLI Cleanup

- [ ] **CLI-03**: User selects a computer folder non-interactively with `--computer NAME` as the sole named-folder flag.
- [ ] **CLI-04**: `--personal`, `--office`, and `--machine` are removed everywhere (parser, mutual-exclusion guards, resolve logic, doc-comment examples) — no dead code paths; passing a removed flag yields a standard argparse "unrecognized argument" error.
- [ ] **CLI-05**: `--help` output references only `--computer` for folder selection (no stale flag mentions).
- [ ] **CLI-06**: The interactive `select_computer` menu and the `--rename` / `--no-commit` / `--archive-days` / `--catalog-dir` flags behave exactly as before (non-regression).

### Versioned Catalog

- [ ] **VER-01**: Homebrew formulae are cataloged with their version.
- [ ] **VER-02**: Homebrew casks are cataloged with their version.
- [ ] **VER-03**: Setapp apps are cataloged with their version (read from `Info.plist`).
- [ ] **VER-04**: Web-installed `/Applications` apps are cataloged with their version (read from `Info.plist`).
- [ ] **VER-05**: When a version can't be determined for an item, the item still appears (name only) and the run never crashes (graceful degradation).
- [ ] **VER-06**: Catalog output stays deterministic and stably sorted — two consecutive runs are diff-empty (preserves FMT-04).

### Retire the zsh Reference

- [ ] **ZSH-01**: `update-list.sh` is removed from the repo.
- [ ] **ZSH-02**: The `zsh_parity` test suite and the CI `zsh -n update-list.sh` integrity gate are removed.
- [ ] **ZSH-03**: Coverage lost with the parity suite is backfilled with direct collector tests; the full suite passes and ruff + `mypy --strict` stay clean.
- [ ] **ZSH-04**: README and docs no longer reference `update-list.sh` or byte-parity; maccat is described as the standalone tool.

## v2 Requirements

Deferred to future releases. Tracked but not in this roadmap.

### Restore / Reinstall

- **RST-01**: Generate a reviewable `reinstall.sh` from a chosen catalog (deterministic sources installed, the rest as a manual checklist; never auto-executed).

### Diffing

- **DIFF-01**: Diff two catalogs over time and report what was added/removed.

### Coverage

- **BRW-01**: Catalog additional browsers/editors (Safari, Edge, Brave, Zed, etc.).
- **CHR-02 / FF-02**: Browser-extension enabled/disabled state.
- **CDX-02**: Codex plugins (when that subsystem ships).

### Distribution

- **PKG-04**: pipx / PyPI as a second distribution channel.

## Out of Scope

Explicitly excluded from v2.0.0. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Maintaining `update-list.sh` in lockstep | The whole point of this milestone is to retire the zsh reference, not keep two implementations in sync |
| Versions for the extension/MCP/plugin sections | Those already emit `name (version) [id]` where obtainable; only the four software sources lack versions |
| Re-deriving version from package metadata when the source CLI/plist doesn't provide it | Graceful degradation (name only) is sufficient; no extra lookups |
| Cross-platform support (Linux/Windows) | macOS-only by design |
| JSON/HTML output formats | Output stays plain-text sectioned |
| Restore/reinstall, diffing, new browsers, PyPI | Separate future milestones (see v2 Requirements) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-03 | Phase 21 | Pending |
| CLI-04 | Phase 21 | Pending |
| CLI-05 | Phase 21 | Pending |
| CLI-06 | Phase 21 | Pending |
| VER-01 | Phase 22 | Pending |
| VER-02 | Phase 22 | Pending |
| VER-03 | Phase 22 | Pending |
| VER-04 | Phase 22 | Pending |
| VER-05 | Phase 22 | Pending |
| VER-06 | Phase 22 | Pending |
| ZSH-01 | Phase 23 | Pending |
| ZSH-02 | Phase 23 | Pending |
| ZSH-03 | Phase 23 | Pending |
| ZSH-04 | Phase 23 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-16*
*Last updated: 2026-06-16 — traceability table filled (roadmap v2.0.0 created)*
