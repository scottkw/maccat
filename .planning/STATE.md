---
gsd_state_version: 1.0
milestone: v2.2.0
milestone_name: Broader Coverage
status: Awaiting next milestone
stopped_at: context exhaustion at 75% (2026-06-17)
last_updated: "2026-06-17T21:22:23.022Z"
last_activity: 2026-06-17 — Milestone v2.2.0 completed and archived
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 5
  completed_plans: 5
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-16)

**Core value:** A single run produces one complete, restorable snapshot of a machine's software *and* tooling extensions — accurate enough to rebuild the environment from, degrading gracefully when any source isn't installed.
**Current focus:** Milestone complete

## Current Position

Phase: Milestone v2.2.0 complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-06-17 — Milestone v2.2.0 completed and archived

## Performance Metrics

**Velocity:**

- Total plans completed: 38 (prior milestones)
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 27. Codex Plugins + Zed Extensions | 0/TBD | - | - |
| 28. Chromium Refactor + Edge + Brave | 0/TBD | - | - |
| 29. Safari Extensions | 0/TBD | - | - |
| 27 | 2 | - | - |
| 28 | 2 | - | - |
| 29 | 1 | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Roadmap (2026-06-17):** 3 phases (coarse granularity), Phases 27-29. Order: independent low-risk sources first (Codex plugins + Zed), then the Chromium refactor + Edge + Brave (refactor must land before subclasses), then Safari last (highest failure modes — undocumented pluginkit subprocess + chained plist reads; isolated so it can be deferred without blocking prior phases).
- **Phase 27 scope:** Extend `CodexCollector.collect()` to return 2 sections (mirror `ClaudeCollector` multi-section pattern); text-grep `~/.codex/config.toml` headers only (FMT-03 — never read plugin bundle `.mcp.json`); degrades to `(none found)` on v0.46.0 (no plugin system). New `ZedCollector` parsing `~/Library/Application Support/Zed/extensions/index.json`; filter `"dev": true` entries; `data.get("extensions", {})` (never `data["extensions"]`). Add section-title uniqueness test for all 19 titles in this phase.
- **Phase 28 scope:** Extract `ChromiumBaseCollector` to `collectors/chromium.py` (shared `_collect_profile()`, `collect()`, base `COMPONENT_DENYLIST`); `chrome.py` becomes thin subclass; re-export `COMPONENT_DENYLIST` from `chrome.py` for backward compat. Update `test_chrome.py` patches to `patch.object(ChromeCollector, "_base", new=tmp_path)`. `BraveCollector`: 20-ID `BRAVE_COMPONENT_DENYLIST` (confirmed from Brave wiki). `EdgeCollector`: Chrome-baseline denylist + documented gap (verify during implementation). Presence detection: base-dir check triggers NOTE only; profile loop handles NativeMessagingHosts-only case silently.
- **Phase 29 scope:** `SafariCollector` shells to `pluginkit -v -m -A -p com.apple.Safari.web-extension`; reads each `.appex` `Info.plist` via `plistlib`; name = `CFBundleDisplayName` (NOT `CFBundleName` = `"safari"`); version = `CFBundleShortVersionString` (NOT pluginkit parenthetical — can be `(null)`); id = `CFBundleIdentifier`. Every plist read individually wrapped in try/except. Validate `_parse_pluginkit_output` against real pluginkit output before closing the phase. Smoke test with Bitwarden (`com.bitwarden.desktop.safari`).
- **Cross-cutting:** All new sections: stdlib-only (no new pip deps); FMT-01/FMT-03/FMT-04; reinstall pipeline zero changes (new section titles fall through to manual checklist by design); `__init__.py` registry updated to 22-section order (Homebrew → mas → Setapp → WebApps → Claude x3 → Codex MCP Servers + Codex Plugins → OpenCode x3 → Gemini x2 → VS Code → Cursor → Zed → Chrome → Edge → Brave → Safari → Firefox).

### Pending Todos

None.

### Blockers/Concerns

- **Edge denylist gap:** No single authoritative Microsoft source for Edge component extension IDs. Ship with Chrome baseline; verify against a real Edge install during Phase 28 implementation; document as known gap in `EDGE_COMPONENT_DENYLIST` constant comment.
- **Safari pluginkit format:** Undocumented internal tool; output format may vary across macOS versions. Mitigated by per-extension individual try/except and a live smoke test requirement before Phase 29 close.
- **Codex v0.46.0:** Plugin system not present until v0.117.0. The "Codex Plugins" section will emit `(none found)` on the current machine — this is the expected behavior, not a bug.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Browser state | CHR-02 / FF-02 — extension enabled/disabled state | v2+ | 2026-06-12 |
| Distribution | PKG-04 — pipx/PyPI as second distribution channel | future | 2026-06-14 |
| Stale artifact | Quick task `260614-ckx-fix-interactive-machine-label-ux` (status: missing) — predates v2.0.0, not in scope; acknowledged at v2.0.0 close | deferred | 2026-06-16 |
| Code hygiene | ~88 stale `update-list.sh:NNNN` code-comment cross-refs (out of ZSH-04 scope) — future comment-cleanup pass | deferred | 2026-06-16 |
| Edge denylist | Complete Edge component ID denylist (beyond Chrome baseline) — requires real Edge install | v2+ | 2026-06-17 |
| Safari content blockers | SAF-02 — `com.apple.Safari.content-blocker` plugin point | v2+ | 2026-06-17 |

## Session Continuity

Last session: 2026-06-17
Stopped at: v2.2.0 SHIPPED — milestone audit PASSED (5/5), complete-milestone done (archived,
  REQUIREMENTS.md removed, tag v2.2.0 created local), tree clean, 628 tests green. Paused before
  finishing doc-polish (context limit). Cleared context here.
Resume file: None — resume checklist is below under "Operator Next Steps".

## Operator Next Steps

**Resume v2.2.0 close — remaining DOC-POLISH only (no code/git-consistency work left):**

1. **Evolve PROJECT.md** — it still lists "## Current Milestone: v2.2.0 Broader Coverage" as ACTIVE.
   Flip it: add a v2.2.0 bullet to "## Shipped Milestones", replace the Current Milestone section
   with a "## Current State" (no active milestone), move BRW-01/BRW-02/BRW-03/BRW-04 + CDX-02 from
   Active → Validated (`- ✓ … — v2.2.0`), drop the now-shipped items from "Next Candidate Milestones",
   and update the footer. (Mirror exactly how v2.1.0 was evolved in PROJECT.md.)
2. **RETROSPECTIVE.md** — append a "## Milestone: v2.2.0 — Broader Coverage" section (what built /
   worked / inefficient / patterns / lessons) before "## Cross-Milestone Trends"; add a v2.2.0 row to
   the trends table. (Note the two process incidents: gsd-sdk npx-cache eviction; the Phase 29
   stale-worktree near-clobber.)
3. **Phase-dir cleanup** — run /gsd-cleanup to archive .planning/phases/27,28,29 →
   milestones/v2.2.0-phases/ (it dry-runs + asks before moving). All earlier milestones already archived.
4. **Push (user-gated, outward-facing)** — tag `v2.2.0` is LOCAL ONLY. `git push && git push origin
   v2.2.0` publishes the GitHub Release; the FIXED release.yml now stamps __version__/pyproject from
   the tag, so the released maccat.pyz will report `maccat 2.2.0` (no manual bump needed). Do NOT push
   without the user; pushing the tag triggers the public release.

**Open/deferred (already documented, non-blocking):** stale quick task
`260614-ckx-fix-interactive-machine-label-ux` (status missing, pre-v2.0.0, re-acknowledged);
documented Edge component-denylist gap (no authoritative Microsoft list).

**Then:** start the next milestone with /gsd-new-milestone.
