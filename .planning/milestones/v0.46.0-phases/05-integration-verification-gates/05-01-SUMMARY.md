---
phase: 05-integration-verification-gates
plan: "01"
subsystem: generate_catalog
tags: [wiring, integration, collectors, zsh]
dependency_graph:
  requires: [04-browser-collectors, 03-ai-cli-collectors, 02-editor-extension-collectors, 01-shared-helpers-foundation]
  provides: [generate_catalog-wired, full-catalog-run]
  affects: [update-list.sh]
tech_stack:
  added: []
  patterns: [function-call-wiring, graceful-degradation]
key_files:
  modified: [update-list.sh]
decisions:
  - "Insert wiring block after Web-installed Applications sort line (line 1463), before generate_catalog closing brace (line 1464) — matches locked CONTEXT.md order"
  - "3-group comment structure: AI CLI Extensions, Editor Extensions, Browser Extensions — mirrors existing code style"
metrics:
  duration_minutes: 2
  completed: "2026-06-13"
  tasks_completed: 1
  tasks_total: 1
---

# Phase 05 Plan 01: Wire 13 Collector Calls into generate_catalog Summary

**One-liner:** Inserted 13 collect_* function calls into generate_catalog — 9 AI CLI, 2 editor, 2 browser — in locked order after the Web-installed Applications block, completing the full catalog pipeline.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Insert 13-call wiring block into generate_catalog | 5fe9321 | update-list.sh (+28 lines) |

## What Was Built

A single targeted edit to `update-list.sh` inserted exactly 28 lines between the Web-installed Applications `sort >> "$OUTPUT_FILE"` pipeline and the closing `}` of `generate_catalog`. The block is organized into three comment-delimited groups:

1. **AI CLI Extensions & Plugins** (9 calls): collect_claude_plugins, collect_claude_mcp, collect_claude_skills_agents, collect_codex_mcp, collect_opencode_plugins, collect_opencode_mcp, collect_opencode_agents, collect_gemini_extensions, collect_gemini_mcp
2. **Editor Extensions** (2 calls): collect_vscode_extensions, collect_cursor_extensions
3. **Browser Extensions** (2 calls): collect_chrome_extensions, collect_firefox_extensions

## Verification Results

- `zsh -n update-list.sh` — SYNTAX OK
- `awk '/^generate_catalog/,/^git_pull/' update-list.sh | grep -c "collect_"` — returns **13** (exact)
- All 13 calls appear in locked order (confirmed by grep listing)
- `git diff update-list.sh` — shows exactly 28 inserted lines, zero changes outside the wiring block
- Existing sections (Homebrew, App Store, Setapp, Web-installed), archive flow, git_pull, and git_commit_and_push are byte-unchanged

## Deviations from Plan

None — plan executed exactly as written. The exact block from 05-RESEARCH.md "Code Examples / Wiring Block" was inserted verbatim at the specified insertion point.

## Known Stubs

None. The wiring block adds only function calls; each collector already writes its own section and degrades gracefully when its source is absent.

## Threat Flags

No new threat surface introduced. The wiring block contains zero new file reads, zero new external commands, zero new variables — only function calls to already-verified collectors. T-05-02 (tampering) disposition: accepted — git diff reviewed and shows only the 13 wiring call lines.

## Self-Check: PASSED

- update-list.sh exists: FOUND
- Commit 5fe9321 exists: FOUND
- 13 collect_ calls in generate_catalog: CONFIRMED (count = 13)
- zsh -n exits 0: CONFIRMED
