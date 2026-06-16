# Roadmap: Mac Software List Generator

## Milestones

- ✅ **v0.46.0 Extension Cataloging** — Phases 1-5 (shipped 2026-06-13) — [archive](milestones/v0.46.0-ROADMAP.md)
- ✅ **v0.47.0 Catalog Retention & Sync** — Phase 6 (shipped 2026-06-14) — [archive](milestones/v0.47.0-ROADMAP.md)
- ✅ **v0.48.0 Machine Identity & Retention Control** — Phases 7-9 (shipped 2026-06-14) — [archive](milestones/v0.48.0-ROADMAP.md)
- ✅ **v0.49.0 Computer-Folder Model** — Phases 10-12 (shipped 2026-06-14) — [archive](milestones/v0.49.0-ROADMAP.md)
- ✅ **v1.0.0 Python Port & Distribution** — Phases 13-17 (shipped 2026-06-14) — [archive](milestones/v1.0.0-ROADMAP.md)
- ✅ **v1.1.0 Repo Separation & CI Build** — Phases 18-20 (shipped 2026-06-16) — [archive](milestones/v1.1.0-ROADMAP.md)
- ✅ **v2.0.0 Standalone maccat — CLI Cleanup & Versioned Catalog** — Phases 21-23 (shipped 2026-06-16) — [archive](milestones/v2.0.0-ROADMAP.md)
- 🔄 **v2.1.0 Reinstall from Catalog** — Phases 24-26 (active)

## Phases

<details>
<summary>✅ v0.46.0 Extension Cataloging (Phases 1-5) — SHIPPED 2026-06-13</summary>

- [x] Phase 1: Shared Helpers Foundation (1/1 plans) — completed 2026-06-13
- [x] Phase 2: Editor Collectors (2/2 plans) — completed 2026-06-13
- [x] Phase 3: AI-CLI Collectors (4/4 plans) — completed 2026-06-13
- [x] Phase 4: Browser Collectors (3/3 plans) — completed 2026-06-13
- [x] Phase 5: Integration & Verification Gates (2/2 plans) — completed 2026-06-13

Full details: [milestones/v0.46.0-ROADMAP.md](milestones/v0.46.0-ROADMAP.md)

</details>

<details>
<summary>✅ v0.47.0 Catalog Retention & Sync (Phase 6) — SHIPPED 2026-06-14</summary>

- [x] Phase 6: Retention & Sync (1/1 plans) — completed 2026-06-14

Full details: [milestones/v0.47.0-ROADMAP.md](milestones/v0.47.0-ROADMAP.md)

</details>

<details>
<summary>✅ v0.48.0 Machine Identity & Retention Control (Phases 7-9) — SHIPPED 2026-06-14</summary>

- [x] Phase 7: Archive Retention Control (1/1 plans) — completed 2026-06-14
- [x] Phase 8: Machine Identity (1/1 plans) — completed 2026-06-14
- [x] Phase 9: Machine Rename (1/1 plans) — completed 2026-06-14

Full details: [milestones/v0.48.0-ROADMAP.md](milestones/v0.48.0-ROADMAP.md)

</details>

<details>
<summary>✅ v0.49.0 Computer-Folder Model (Phases 10-12) — SHIPPED 2026-06-14</summary>

- [x] Phase 10: Computer-Folder Identity Foundation (1/1 plans) — completed 2026-06-14
- [x] Phase 11: Computer Selection & CLI (2/2 plans) — completed 2026-06-14
- [x] Phase 12: Computer Rename (2/2 plans) — completed 2026-06-14

Full details: [milestones/v0.49.0-ROADMAP.md](milestones/v0.49.0-ROADMAP.md)

</details>

<details>
<summary>✅ v1.0.0 Python Port & Distribution (Phases 13-17) — SHIPPED 2026-06-14</summary>

Full phase detail: [milestones/v1.0.0-ROADMAP.md](milestones/v1.0.0-ROADMAP.md)

- [x] Phase 13: Package Foundation + Output Format (3/3 plans) — completed 2026-06-14
- [x] Phase 14: Config, Identity & Retention (4/4 plans) — completed 2026-06-14
- [x] Phase 15: Collectors (8/8 plans) — completed 2026-06-15
- [x] Phase 16: Git, CLI & Distribution (3/3 plans) — completed 2026-06-15
- [x] Phase 17: Parity & Safety Tests (3/3 plans) — completed 2026-06-15

</details>

<details>
<summary>✅ v1.1.0 Repo Separation & CI Build (Phases 18-20) — SHIPPED 2026-06-16</summary>

- [x] Phase 18: Public Repo Migration (Genericized, Fresh History) (2/2 plans) — completed 2026-06-16
- [x] Phase 19: CI Build & Release Pipeline (2/2 plans) — completed 2026-06-16
- [x] Phase 20: Cut-Over & External-Catalog Verification (2/2 plans) — completed 2026-06-16

Full details: [milestones/v1.1.0-ROADMAP.md](milestones/v1.1.0-ROADMAP.md)

</details>

<details>
<summary>✅ v2.0.0 Standalone maccat — CLI Cleanup & Versioned Catalog (Phases 21-23) — SHIPPED 2026-06-16</summary>

Full phase details archived in [milestones/v2.0.0-ROADMAP.md](milestones/v2.0.0-ROADMAP.md).

- [x] Phase 21: CLI Cleanup (2/2 plans) — completed 2026-06-16
- [x] Phase 22: Versioned Catalog (3/3 plans) — completed 2026-06-16
- [x] Phase 23: Retire the zsh Reference (3/3 plans) — completed 2026-06-16

</details>

### v2.1.0 Reinstall from Catalog (Phases 24-26)

- [x] **Phase 24: Catalog Format Fix + Parser Foundation** — MasCollector emits App Store ID; reverse parser with round-trip contract test (completed 2026-06-16)
- [ ] **Phase 25: Script Emitter** — All auto-install renderers (brew/mas/extensions) + manual checklist + script structure + injection safety
- [ ] **Phase 26: Picker + CLI Wiring + Integration** — `--from`/interactive picker + `maccat reinstall` subcommand wired into `cli.py`

## Phase Details

### Phase 24: Catalog Format Fix + Parser Foundation
**Goal**: The App Store ID is preserved in the catalog and the catalog can be parsed back into typed structured items
**Depends on**: Nothing (first phase of milestone)
**Requirements**: MAS-01, PARSE-01
**Success Criteria** (what must be TRUE):
  1. A catalog generated after this phase includes the App Store numeric ID in every mas entry: `AppName (version) [id]` — no double-parenthesized version, no missing bracket
  2. The existing mas collector tests pass with updated assertions reflecting the new format
  3. `parse_catalog(path)` returns a `ParsedCatalog` whose items correctly reflect name, version, and id for all four `emit_item` line shapes, including graceful handling of the `(none found)` sentinel and collector degradation messages
  4. The round-trip contract test in `tests/reinstall/test_parser_contract.py` passes for all six `emit_item` degradation variants, including adversarial fixtures with embedded parentheses in names
**Plans**: 2 plans
Plans:
- [x] 24-01-PLAN.md — Rewrite MasCollector._parse_mas_output + update TestMasCollector assertions (MAS-01)
- [x] 24-02-PLAN.md — Create reinstall/ subpackage (parser.py dataclasses + ITEM_RE + parse_catalog) + round-trip contract tests (PARSE-01)

### Phase 25: Script Emitter
**Goal**: A `ParsedCatalog` can be rendered into a complete, injection-safe, idempotent `reinstall.sh` script string
**Depends on**: Phase 24
**Requirements**: GEN-01, GEN-02, GEN-03, GEN-04, MAN-01
**Success Criteria** (what must be TRUE):
  1. A generated script passes `bash -n reinstall.sh` (syntax-valid bash) and opens with `#!/usr/bin/env bash` + `set -Eeuo pipefail` + a provenance header naming the source catalog and generation date
  2. Every Homebrew line uses the `brew list --cask <n> &>/dev/null || brew install` idempotency guard and carries a `# cataloged: version` comment; App Store entries with an ID emit a `mas install <id>` guard line; App Store entries without an ID (pre-MAS-01 catalogs) appear only in the manual checklist
  3. VS Code and Cursor extension lines include a `command -v` PATH guard, a `--list-extensions | grep -qi` idempotency check, and use the lowercased marketplace ID as the install key
  4. Setapp apps, web-installed apps, browser extensions, and all AI-CLI tooling (MCP servers, plugins, skills, agents) appear exclusively in the manual checklist as `echo` statements — no fabricated install commands are emitted for these sources
  5. Every catalog-derived value inserted into shell command position is processed through `shlex.quote()` — no bare f-string interpolation in shell context
**Plans**: 1 plan
Plans:
- [ ] 25-01-PLAN.md — emitter.py + test_emitter.py (all renderers, injection safety, bash -n test)

### Phase 26: Picker + CLI Wiring + Integration
**Goal**: `maccat reinstall` is a working subcommand that resolves a catalog, generates `reinstall.sh`, and prints its path
**Depends on**: Phase 25
**Requirements**: RST-01, RST-02
**Success Criteria** (what must be TRUE):
  1. `maccat reinstall --from path/to/catalog.txt` writes `reinstall.sh` to the current directory, prints its absolute path to stdout, and exits 0 — the file is mode 0644 (not executable) and was never subprocess-run
  2. `maccat reinstall` without `--from` invokes the existing interactive computer-picker (`select_computer`) and uses the newest catalog in the selected computer's folder — the `--computer NAME` flag flows through for non-interactive selection
  3. The existing 13-step catalog-gen path in `cli.py run()` is unchanged — `maccat catalog` (or any non-reinstall invocation) behaves identically to before this phase
  4. Running `maccat reinstall --from <fixture>` in an integration test confirms the output file exists, contains the expected shebang and provenance header, and the `--rename` guard does not fire
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 24 → 25 → 26

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Shared Helpers Foundation | v0.46.0 | 1/1 | Complete | 2026-06-13 |
| 2. Editor Collectors | v0.46.0 | 2/2 | Complete | 2026-06-13 |
| 3. AI-CLI Collectors | v0.46.0 | 4/4 | Complete | 2026-06-13 |
| 4. Browser Collectors | v0.46.0 | 3/3 | Complete | 2026-06-13 |
| 5. Integration & Verification Gates | v0.46.0 | 2/2 | Complete | 2026-06-13 |
| 6. Retention & Sync | v0.47.0 | 1/1 | Complete | 2026-06-14 |
| 7. Archive Retention Control | v0.48.0 | 1/1 | Complete | 2026-06-14 |
| 8. Machine Identity | v0.48.0 | 1/1 | Complete | 2026-06-14 |
| 9. Machine Rename | v0.48.0 | 1/1 | Complete | 2026-06-14 |
| 10. Computer-Folder Identity Foundation | v0.49.0 | 1/1 | Complete | 2026-06-14 |
| 11. Computer Selection & CLI | v0.49.0 | 2/2 | Complete | 2026-06-14 |
| 12. Computer Rename | v0.49.0 | 2/2 | Complete | 2026-06-14 |
| 13. Package Foundation + Output Format | v1.0.0 | 3/3 | Complete | 2026-06-14 |
| 14. Config, Identity & Retention | v1.0.0 | 4/4 | Complete | 2026-06-14 |
| 15. Collectors | v1.0.0 | 8/8 | Complete | 2026-06-15 |
| 16. Git, CLI & Distribution | v1.0.0 | 3/3 | Complete | 2026-06-15 |
| 17. Parity & Safety Tests | v1.0.0 | 3/3 | Complete | 2026-06-15 |
| 18. Public Repo Migration | v1.1.0 | 2/2 | Complete | 2026-06-16 |
| 19. CI Build & Release Pipeline | v1.1.0 | 2/2 | Complete | 2026-06-16 |
| 20. Cut-Over & External-Catalog Verification | v1.1.0 | 2/2 | Complete | 2026-06-16 |
| 21. CLI Cleanup | v2.0.0 | 2/2 | Complete | 2026-06-16 |
| 22. Versioned Catalog | v2.0.0 | 3/3 | Complete | 2026-06-16 |
| 23. Retire the zsh Reference | v2.0.0 | 3/3 | Complete | 2026-06-16 |
| 24. Catalog Format Fix + Parser Foundation | v2.1.0 | 2/2 | Complete    | 2026-06-16 |
| 25. Script Emitter | v2.1.0 | 0/TBD | Not started | - |
| 26. Picker + CLI Wiring + Integration | v2.1.0 | 0/TBD | Not started | - |
