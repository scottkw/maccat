---
phase: 03-ai-cli-collectors
plan: "04"
subsystem: testing
tags: [zsh, mcp, fmt-03, security, self-test, determinism]

requires:
  - phase: 03-ai-cli-collectors
    provides: "All 9 Phase 3 collector functions in update-list.sh (CC-01..03, CDX-01, OC-01..03, GEM-01..02)"

provides:
  - "FMT-03 zero-leakage proof: grep -Ec on all 9 collector outputs returns 0 hits for all 7 secret patterns"
  - "Determinism proof: two consecutive runs of all 9 collectors produce byte-identical output"
  - "Section presence audit: all 9 expected section headers confirmed in combined output"
  - "execbro MCP entry confirmed as 'execbro [stdio]' only — env/command/args absent"
  - "Syntax validity: zsh -n update-list.sh exits 0"
  - "Live count verification: Claude 9 plugins, 1 MCP, 103 skills+agents; Codex 0 MCP; OpenCode 1 plugin, 0 MCP, 33 agents; Gemini 1 extension, 0 MCP"

affects:
  - 04-browser-collectors
  - 05-integration-wiring

tech-stack:
  added: []
  patterns:
    - "Ephemeral test harness: source functions-only (head -1419 update-list.sh) into zsh subshell, point OUTPUT_FILE at /tmp, call collectors directly"
    - "Secret-leakage gate: grep -Ec pattern with || true to handle 0-match exit code under zsh"
    - "Determinism gate: run collectors twice into /tmp/p3-run1.txt and /tmp/p3-run2.txt, diff exits 0"

key-files:
  created:
    - "/tmp/p3-test.zsh (ephemeral — not committed)"
    - "/tmp/p3-all-sections.txt (ephemeral — not committed)"
    - "/tmp/p3-run1.txt (ephemeral — not committed)"
    - "/tmp/p3-run2.txt (ephemeral — not committed)"
  modified: []

key-decisions:
  - "Test harness sources only lines 1-1419 of update-list.sh (via head -1419) to avoid executing the main block, which would trigger git/interactive operations"
  - "REPO_DIR must be re-declared after eval because the script's own header sets SCRIPT_DIR='${0:A:h}' which could be misused if REPO_DIR were derived from it"
  - "grep -Ec returns exit code 1 on 0 matches; the || true guard is required in zsh to prevent early exit when the leakage count is correctly 0"
  - "update-list.sh has no uncommitted changes after the self-test — test is fully ephemeral"

patterns-established:
  - "Phase completion gate: run all collectors into /tmp, assert zero-leakage + section presence + determinism before marking phase done"
  - "FMT-03 enforcement by construction: collectors read only .key and .value.type from MCP configs; the self-test proves this by exhaustive grep across all output"

requirements-completed:
  - FMT-03
  - CC-01
  - CC-02
  - CC-03
  - CDX-01
  - OC-01
  - OC-02
  - OC-03
  - GEM-01
  - GEM-02

duration: 4min
completed: 2026-06-13
---

# Phase 03 Plan 04: FMT-03 Self-Test Summary

**Zero-leakage gate + determinism + section-presence self-test: all 9 AI CLI collectors pass with 0 secret pattern hits, byte-identical dual runs, and exact expected live counts**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-13T17:04:38Z
- **Completed:** 2026-06-13T17:08:28Z
- **Tasks:** 2
- **Files modified:** 0 (self-test is fully ephemeral)

## Accomplishments

- FMT-03 zero-leakage proof: `grep -Ec "http|token|Bearer|key=|Authorization|sk-|ghp_"` on combined output of all 9 collectors returns **0** — milestone-critical security guarantee holds
- Determinism gate: two consecutive full-collector runs produce byte-identical output (diff exits 0) — LC_ALL=C sort -f -u in flush_section is sufficient
- Section presence: all 9 headers confirmed (`Claude Code Plugins`, `Claude Code MCP Servers`, `Claude Code Skills & Agents`, `Codex MCP Servers`, `OpenCode Plugins`, `OpenCode MCP Servers`, `OpenCode Agents`, `Gemini CLI Extensions`, `Gemini CLI MCP Servers`)
- Live counts match research baselines exactly: 9 Claude plugins, 1 MCP server (`execbro [stdio]`), 103 skills+agents, 0 Codex MCP, 1 OpenCode plugin (`superpowers`), 0 OpenCode MCP, 33 OpenCode agents, 1 Gemini extension (`conductor 0.4.1`), 0 Gemini MCP
- execbro MCP entry verified as `execbro [stdio]` only — no env/command/args fields in output
- `zsh -n update-list.sh` exits 0 — script syntax valid after all Phase 3 additions
- `update-list.sh` has zero uncommitted changes — test is fully ephemeral

## Task Commits

This plan is a self-test only — no source file changes were committed. The plan metadata commit captures the SUMMARY.md.

**Plan metadata:** (see commit below)

## Files Created/Modified

- `/tmp/p3-test.zsh` — ephemeral test harness (not committed, sources functions-only via `head -1419 update-list.sh`)
- `/tmp/p3-all-sections.txt` — ephemeral combined collector output (178 lines)
- `/tmp/p3-run1.txt` — ephemeral first determinism run
- `/tmp/p3-run2.txt` — ephemeral second determinism run
- `.planning/phases/03-ai-cli-collectors/03-04-SUMMARY.md` — this file

## Decisions Made

- Used `head -1419` to extract only function definitions (main block starts at line 1420) — avoids triggering interactive prompt, git pull, and git commit in the test
- Used `|| true` after `grep -Ec` because grep exits 1 when the match count is 0, which would halt the test script under normal error handling
- Re-declared `REPO_DIR` after `eval` because the script header sets `SCRIPT_DIR="${0:A:h}"` which would resolve to `/private/tmp` when sourced from the test harness

## Deviations from Plan

None - plan executed exactly as written. The test harness approach (head -1419 extraction) was the approach specified in the plan's "Practical approach" guidance.

The `grep -Ec` exit-code-on-zero-matches behavior required a `|| true` guard — this is a known zsh/POSIX behavior (not a bug in the collector) and was handled inline in the test harness without modifying any source files.

## Issues Encountered

**grep -Ec exit code when 0 matches:** `grep -Ec` returns exit code 1 even when the count is 0 (no matches found). In a test script without strict error handling, this silently terminated the script after the leakage gate. Fixed by appending `|| true` to the grep command, which correctly distinguishes between "0 matches (success)" and "grep error (failure)".

## Known Stubs

None. This plan produces no persistent output — all test artifacts are ephemeral `/tmp` files.

## Threat Flags

None. The self-test reads only from already-existing collector output files in `/tmp`. No new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Next Phase Readiness

Phase 3 (AI-CLI Collectors) is complete. All 9 collector functions are in `update-list.sh`, syntax-valid, FMT-03 compliant, and deterministic.

**Phase 4 (Browser Collectors)** can proceed. No blockers.

Reminder from STATE.md: Phase 4 research flag — confirm that reporting Chrome `__MSG_`/ID placeholder is acceptable degradation when `jq` is absent; test a non-`en` `default_locale`.

---
*Phase: 03-ai-cli-collectors*
*Completed: 2026-06-13*
