# Requirements: maccat — v2.1.0 Reinstall from Catalog

**Defined:** 2026-06-16
**Core Value:** A single run produces one complete, restorable snapshot of a machine's software *and* tooling extensions — accurate enough to rebuild the environment from, degrading gracefully when any source isn't installed.

## v1 Requirements

Requirements for this milestone (v2.1.0). Each maps to a roadmap phase.

### Catalog Format

- [x] **MAS-01**: The App Store section preserves the numeric App Store ID — emits `AppName (version) [id]` (the version is not double-parenthesized; `mas list` column 3 already wraps it in parens). `MasCollector` + its tests are updated. (No parity suite to break — retired in v2.0.0.)

### Catalog Parsing

- [x] **PARSE-01**: A parser reads a catalog's sectioned plain text back into structured per-source items, honoring `emit_item`'s four line shapes (`name (version) [id]`, `name (version)`, `name [id]`, `name`) and its degradations (id-promoted-to-name, name-only). A round-trip contract test locks the parser ↔ `catalog/format.py` coupling so the two cannot drift.

### Reinstall Command

- [ ] **RST-01**: `maccat reinstall` generates a `reinstall.sh` from a catalog, prints its output path, and never auto-executes it; the file is written non-executable (mode 0644).
- [ ] **RST-02**: `--from PATH` selects an explicit catalog file; if omitted, the existing interactive computer-picker selects a computer and uses that computer's newest catalog (reuses `select_computer` + catalog-dir resolution; the parent `--computer` flag flows through).

### Auto-Install Output

- [x] **GEN-01**: Homebrew packages are emitted as guarded `brew install <name>` lines that install a formula or cask and are safe to re-run (cask idempotency guard); the cataloged version appears as a `# cataloged: …` comment. A name that is both a formula and a cask is noted as needing manual `--cask`/`--formula`.
- [x] **GEN-02**: App Store apps that carry an ID are emitted as `mas install <id>` lines (version as comment); App Store apps from a pre-MAS-01 catalog (no ID) degrade to the manual checklist rather than emitting a broken command.
- [x] **GEN-03**: VS Code and Cursor extensions are emitted as `code --install-extension <id>` / `cursor --install-extension <id>` lines with a PATH guard (`command -v`) and an idempotency guard (`--list-extensions` pre-check or `--force`); ids lowercased.
- [x] **GEN-04**: The generated script uses `#!/usr/bin/env bash` + `set -Eeuo pipefail`, opens with a provenance + "review before running" header (source catalog name, generation date), orders sections conventionally (formulae → casks → mas → code → cursor → manual checklist), and `shlex.quote()`s every catalog-derived value (injection-safe).

### Manual Checklist

- [x] **MAN-01**: Non-deterministic sources — Setapp apps, web-installed `/Applications`, Chrome/Firefox extensions, and AI-CLI MCP servers / plugins / skills / agents — are emitted as a manual checklist (runtime `echo` reminders after the automated installs), listed by name. No fabricated install commands.

## v2 Requirements

Deferred to future releases.

### Diffing

- **DIFF-01**: Diff two catalogs over time and report added / removed / version-changed items.

### Coverage

- **BRW-01**: Catalog additional browsers/editors (Safari, Edge, Brave, Zed).
- **CHR-02 / FF-02**: Browser-extension enabled/disabled state.
- **CDX-02**: Codex plugins (when that subsystem ships).

### Distribution

- **PKG-04**: pipx / PyPI as a second distribution channel.

### Reinstall (future enhancements)

- **RST-03**: Auto-install Homebrew taps (the catalog does not currently record the source tap).
- **RST-04**: Best-effort restore of AI-CLI tooling beyond a checklist (would require capturing more than identity, conflicting with FMT-03 — needs a separate design).

## Out of Scope

Explicitly excluded from v2.1.0.

| Feature | Reason |
|---------|--------|
| Auto-executing the generated script | Installing software is high-impact and machine-specific; the user must review and run it themselves |
| Version pinning (install exact cataloged version) | Unreliable across brew/mas/extensions; the cataloged version is a reference comment only |
| Auto-installing Setapp / web apps / browser extensions | No reliable CLI installer keyed on cataloged data — manual checklist only |
| Auto-installing AI-CLI MCP/plugins/skills | Catalog stores identity only (FMT-03 secret-safety) — nothing to install from; manual checklist only |
| Backfilling the mas ID into already-generated catalogs | MAS-01 is go-forward only; rewriting historical catalogs is out of scope |
| Cross-platform support | macOS-only by design |

## Traceability

Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MAS-01 | Phase 24 | Complete |
| PARSE-01 | Phase 24 | Complete |
| RST-01 | Phase 26 | Pending |
| RST-02 | Phase 26 | Pending |
| GEN-01 | Phase 25 | Complete |
| GEN-02 | Phase 25 | Complete |
| GEN-03 | Phase 25 | Complete |
| GEN-04 | Phase 25 | Complete |
| MAN-01 | Phase 25 | Complete |

**Coverage:**
- v1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-16*
*Last updated: 2026-06-16 — traceability filled by roadmap creation (Phases 24-26)*
