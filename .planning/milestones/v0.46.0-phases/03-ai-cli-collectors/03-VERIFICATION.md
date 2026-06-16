---
phase: 03-ai-cli-collectors
verified: 2026-06-13T17:32:10Z
status: passed
score: 10/10
overrides_applied: 0
deferred:
  - truth: "Running update-list.sh produces 'Claude Code Plugins', 'Claude Code MCP Servers', and 'Claude Code Skills & Agents' sections (SC 1)"
    addressed_in: "Phase 5"
    evidence: "Phase 5 SC 1: 'generate_catalog calls every collector in fixed order (AI CLIs → editors → browsers) appended after the existing Web-installed block'. All four PLAN must_haves explicitly state collectors are 'defined functions in update-list.sh but NOT called from generate_catalog' — Phase 5 wires them."
  - truth: "Running update-list.sh produces a 'Codex MCP Servers' section (SC 2)"
    addressed_in: "Phase 5"
    evidence: "Same as above — Phase 5 SC 1 wires all collectors. The collect_codex_mcp function is fully implemented, syntax-valid, and produces correct output when called directly."
  - truth: "Running update-list.sh produces 'OpenCode Plugins', 'OpenCode MCP Servers', and 'OpenCode Agents' sections (SC 3)"
    addressed_in: "Phase 5"
    evidence: "Same as above — Phase 5 SC 1. All three OpenCode collectors are fully implemented and verified."
  - truth: "Running update-list.sh produces 'Gemini CLI Extensions' and 'Gemini CLI MCP Servers' sections (SC 4)"
    addressed_in: "Phase 5"
    evidence: "Same as above — Phase 5 SC 1. Both Gemini collectors are fully implemented and verified."
---

# Phase 3: AI-CLI Collectors Verification Report

**Phase Goal:** A single run catalogs the plugins, MCP servers, and skills/agents of Claude Code, Codex, OpenCode, and Gemini — capturing identity only, never secrets
**Verified:** 2026-06-13T17:32:10Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All must-haves are drawn from the merged set of PLAN frontmatter truths (03-01 through 03-04).
The four ROADMAP success criteria that express "Running update-list.sh produces..." are deferred
to Phase 5 by explicit design — see Deferred Items section below.

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | All 9 collector functions are defined in update-list.sh | VERIFIED | `grep -c "^collect_…()"` returns 9/9 |
| 2  | Claude Code Plugins collector emits 9 entries as `name (version) [id]` | VERIFIED | Live output: 9 lines with `@` IDs (claude-mem, dev-browser, frontend-design, gopls-lsp, pyright-lsp, superpowers, typescript-lsp, ui-ux-pro-max, warp) |
| 3  | Claude Code MCP collector emits exactly `execbro [stdio]` and zero secret fields | VERIFIED | `grep "execbro"` in output = `execbro [stdio]`; no env/command/args fields present |
| 4  | No MCP output line contains env, token, key=, Bearer, sk-, ghp_, Authorization, or any http URL | VERIFIED | `grep -Ec "http|token|Bearer|key=|Authorization|sk-|ghp_"` on combined 9-collector output = **0** |
| 5  | No MCP output line contains /Users/ path leakage | VERIFIED | `grep -Ec "/Users/"` on combined output = **0** |
| 6  | Claude Code Skills & Agents collector enumerates all 70 skills and 33 agents (103 total) | VERIFIED | Awk count on output section = 103; `ls ~/.claude/skills/ | wc -l` = 70, `ls ~/.claude/agents/*.md | wc -l` = 33 |
| 7  | Codex MCP Servers section writes `(none found)` — `codex mcp list --json` returns `[]` | VERIFIED | Output contains `(none found)` under Codex MCP Servers; no Codex plugin/extension section emitted |
| 8  | OpenCode Plugins lists `superpowers`, OpenCode MCP writes `(none found)`, OpenCode Agents lists 33 agents | VERIFIED | Output verified: `superpowers`, `(none found)`, 33 agent names |
| 9  | Gemini CLI Extensions lists `conductor (0.4.1)`, Gemini CLI MCP writes `(none found)` | VERIFIED | Output: `conductor (0.4.1)` from `~/.gemini/extensions/conductor/gemini-extension.json`; MCP `(none found)` via -s guard on 0-byte `mcp_config.json` |
| 10 | All 9 collectors are defined but NOT called from generate_catalog or the main block | VERIFIED | `grep "collect_claude\|collect_codex\|collect_opencode\|collect_gemini" update-list.sh | grep -v "^[0-9]*:collect_\|^[0-9]*:#"` returns empty; `grep "collect_" lines 1252-1317` returns empty |

**Score:** 10/10 truths verified

---

### Deferred Items

Items not yet met by definition — Phase 3 explicitly defers `generate_catalog` wiring to Phase 5.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | ROADMAP SC 1: "Running update-list.sh produces" Claude Code sections | Phase 5 | Phase 5 SC 1: "generate_catalog calls every collector in fixed order"; all 03-0x PLANs state "NOT called from generate_catalog" |
| 2 | ROADMAP SC 2: "Running update-list.sh produces" Codex MCP section | Phase 5 | Same as above |
| 3 | ROADMAP SC 3: "Running update-list.sh produces" OpenCode sections | Phase 5 | Same as above |
| 4 | ROADMAP SC 4: "Running update-list.sh produces" Gemini sections | Phase 5 | Same as above |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `update-list.sh` | `collect_claude_plugins` function | VERIFIED | Line 773; reads `~/.claude/plugins/installed_plugins.json`; jq path + plutil fallback; 9 entries on live machine |
| `update-list.sh` | `collect_claude_mcp` function | VERIFIED | Line 817; reads only `.key` and `.value.type` from `~/.claude.json`; transport clamped to stdio/http/sse; FMT-03 clean |
| `update-list.sh` | `collect_claude_skills_agents` function | VERIFIED | Line 871; skills from `~/.claude/skills/*/SKILL.md`; agents from `~/.claude/agents/*.md`; null_glob guarded; 103 items |
| `update-list.sh` | `collect_codex_mcp` function | VERIFIED | Line 927; CLI-first (`codex mcp list --json`), TOML fallback; WR-01 fix applied (flush/return inside jq block) |
| `update-list.sh` | `collect_opencode_plugins` function | VERIFIED | Line 981; parses `.plugin[]?` from `opencode.json`; WR-02 fix applied (path/URL guard) |
| `update-list.sh` | `collect_opencode_mcp` function | VERIFIED | Line 1040; reads `.mcp` key+type only; WR-03 fix applied (single plutil call) |
| `update-list.sh` | `collect_opencode_agents` function | VERIFIED | Line 1109; `~/.config/opencode/agents/*.md`; 33 entries |
| `update-list.sh` | `collect_gemini_extensions` function | VERIFIED | Line 1149; `~/.gemini/extensions/*/gemini-extension.json`; `json_get` + null_glob |
| `update-list.sh` | `collect_gemini_mcp` function | VERIFIED | Line 1195; `-s` guard for 0-byte file; FMT-03 clean |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `collect_claude_plugins` | `~/.claude/plugins/installed_plugins.json` | `jq .plugins to_entries[]` | VERIFIED | Pattern `installed_plugins.json` at line 774; `${key%%@*}` strips @marketplace suffix |
| `collect_claude_mcp` | `~/.claude.json .mcpServers` | `jq .mcpServers to_entries[] — .key + .value.type ONLY` | VERIFIED | Lines 837-838; zero secret field access confirmed by code scan and live output |
| `collect_claude_skills_agents` | `~/.claude/skills/` and `~/.claude/agents/` | null_glob glob + grep `name:` frontmatter | VERIFIED | Lines 882-910; `setopt local_options null_glob` at line 879 (single call, IN-01 fixed) |
| `collect_codex_mcp` | `codex mcp list --json` → `~/.codex/config.toml` | CLI preferred; TOML grep section headers only | VERIFIED | Lines 935-968; WR-01 fix: flush/return inside jq block; IN-03 fix: TOML comment stripping at line 964 |
| `collect_opencode_plugins` | `~/.config/opencode/opencode.json .plugin` | `jq .plugin[]?` + `${entry%%@*}` | VERIFIED | Lines 993-1005; WR-02 path/URL guard at lines 999-1001 and 1013-1016 |
| `collect_opencode_mcp` | `~/.config/opencode/opencode.json .mcp` | jq key+type only; plutil single-call fallback | VERIFIED | Lines 1052-1093; WR-03 fix: single `plutil -extract "mcp" raw` at line 1073 |
| `collect_opencode_agents` | `~/.config/opencode/agents/*.md` | null_glob + grep `name:` | VERIFIED | Lines 1122-1129; 33 agents enumerated |
| `collect_gemini_extensions` | `~/.gemini/extensions/*/gemini-extension.json` | null_glob + `json_get name` + `json_get version` | VERIFIED | Lines 1162-1172; `conductor (0.4.1)` confirmed |
| `collect_gemini_mcp` | `~/.gemini/config/mcp_config.json` | `[[ -s ]]` nonzero-size guard | VERIFIED | Line 1202; `-s` guard handles 0-byte file; `(none found)` output confirmed |

---

### FMT-03 Zero-Leakage Verification (Milestone-Critical)

This is the milestone-critical check. Ran all 9 collectors via an ephemeral harness sourcing
`update-list.sh` lines 1-1434 (function definitions only, before `generate_catalog` and the
main block) into `zsh`, with `OUTPUT_FILE=/tmp/p3-all-sections.txt`.

**Combined 9-collector output:** 178 lines

**Secret pattern grep results:**

| Pattern | Hits | Status |
|---------|------|--------|
| `http` | 0 | PASS |
| `token` | 0 | PASS |
| `Bearer` | 0 | PASS |
| `key=` | 0 | PASS |
| `Authorization` | 0 | PASS |
| `sk-` | 0 | PASS |
| `ghp_` | 0 | PASS |
| `/Users/` path leakage | 0 | PASS |

**execbro MCP entry:** `execbro [stdio]` — only this line; no env/command/args fields.

**Transport label clamping:** All 4 MCP collectors contain `stdio|http|sse` case whitelist.
Claude MCP: 2 clamp sites, Codex MCP: 1, OpenCode MCP: 2, Gemini MCP: 2.

**Code-level FMT-03 audit:**
- Zero jq expressions accessing `.env`, `.command`, `.args`, `.url`, or `.headers`
- Zero plutil expressions accessing credential-bearing fields
- Codex TOML fallback reads only `[mcp_servers.*]` section header lines, never value lines

**FMT-03 verdict: PASS — zero secret leakage paths by construction and by live proof.**

---

### Determinism Gate

Two consecutive runs of all 9 collectors with no machine changes between runs:
- Run 1: `/tmp/p3-run1.txt`
- Run 2: `/tmp/p3-run2.txt`
- `diff /tmp/p3-run1.txt /tmp/p3-run2.txt` → **exit 0, no output**

**Determinism verdict: PASS — byte-identical output confirmed.**

---

### Data-Flow Trace (Level 4)

All 9 collectors route through `emit_item` → `_section_lines` buffer → `flush_section`
which applies `LC_ALL=C sort -f -u` before writing to `OUTPUT_FILE`. This is the same
pattern established in Phase 1 and used by the Phase 2 editor collectors. No collector
writes directly to `OUTPUT_FILE` outside this flow. Data sources are live filesystem reads
(not hardcoded), confirmed by live output on this machine matching research baselines.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Claude plugins: 9 entries | `awk '/^Claude Code Plugins/{f=1} /^Claude Code MCP/{f=0} f && /\[/' /tmp/p3-all-sections.txt | wc -l` | 9 | PASS |
| Claude MCP: execbro [stdio] only | `grep "execbro" /tmp/p3-all-sections.txt` | `execbro [stdio]` | PASS |
| Skills+agents: 103 entries | `awk '/^Claude Code Skills/{f=1} /^Codex/{f=0} f && /^[a-z]/' /tmp/p3-all-sections.txt | wc -l` | 103 | PASS |
| Codex MCP: (none found) | Section content | `(none found)` | PASS |
| OpenCode plugins: superpowers | Section content | `superpowers` | PASS |
| OpenCode MCP: (none found) | Section content | `(none found)` | PASS |
| OpenCode agents: 33 entries | `awk '/^OpenCode Agents/{f=1} /^Gemini/{f=0} f && /^[a-z]/' ...` | 33 | PASS |
| Gemini extensions: conductor (0.4.1) | Section content | `conductor (0.4.1)` | PASS |
| Gemini MCP: (none found) | Section content | `(none found)` | PASS |
| FMT-03 leakage gate | `grep -Ec "http|token|Bearer|key=|Authorization|sk-|ghp_"` | 0 | PASS |
| Determinism | `diff /tmp/p3-run1.txt /tmp/p3-run2.txt` | exit 0 | PASS |
| Syntax validity | `zsh -n update-list.sh` | exit 0 | PASS |

---

### Code Review Fix Verification

All 7 findings from `03-REVIEW.md` were fixed in `03-REVIEW-FIX.md`. Verified in live code:

| Fix ID | Description | Verified? | Evidence |
|--------|-------------|-----------|---------|
| WR-01 | `collect_codex_mcp` flush/return moved inside jq block | YES | Lines 949-950 are inside `if command -v jq`; jq-absent path falls through to TOML |
| WR-02 | `collect_opencode_plugins` path/URL guard added | YES | Lines 999-1001 and 1013-1016: `[[ "$name" == "$entry" && "$entry" == */* ]]` skip guard |
| WR-03 | `collect_opencode_mcp` consolidated to single plutil call | YES | Lines 1072-1081: single `plutil -extract "mcp" raw` into `server_names` array |
| WR-04 | `collect_claude_skills_agents` name reset at loop start | YES | Line 885: `name=""` before `local skill_md=` inside the for loop |
| IN-01 | `collect_claude_skills_agents` duplicate setopt removed | YES | Line 879: single `setopt local_options null_glob`; no second call in agents block |
| IN-02 | `collect_claude_plugins` `local ver` moved to preamble | YES | Line 775: `local name="" version="" key="" ver=""` |
| IN-03 | `collect_codex_mcp` TOML inline comment stripping added | YES | Line 964: `sed 's/[[:space:]]*#.*$//'` in TOML pipeline |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| CC-01 | 03-01-PLAN.md | Catalog Claude Code plugins (name + version + ID) | SATISFIED | `collect_claude_plugins` emits 9 entries in `name (version) [id]` format |
| CC-02 | 03-01-PLAN.md | Catalog Claude Code MCP servers (name + transport only) | SATISFIED | `collect_claude_mcp` emits `execbro [stdio]`; FMT-03 clean |
| CC-03 | 03-01-PLAN.md | Catalog Claude Code skills and subagents | SATISFIED | `collect_claude_skills_agents` emits 103 items (70 skills + 33 agents) |
| CDX-01 | 03-02-PLAN.md | Catalog Codex MCP servers | SATISFIED | `collect_codex_mcp` works; returns `(none found)` for this machine |
| OC-01 | 03-02-PLAN.md | Catalog OpenCode plugins | SATISFIED | `collect_opencode_plugins` emits `superpowers` |
| OC-02 | 03-02-PLAN.md | Catalog OpenCode MCP servers | SATISFIED | `collect_opencode_mcp` emits `(none found)` for null .mcp field |
| OC-03 | 03-02-PLAN.md | Catalog OpenCode agents | SATISFIED | `collect_opencode_agents` emits 33 agents |
| GEM-01 | 03-03-PLAN.md | Catalog Gemini CLI extensions (name + version + ID) | SATISFIED | `collect_gemini_extensions` emits `conductor (0.4.1)`; no ID field in manifest = graceful FMT-01 degradation |
| GEM-02 | 03-03-PLAN.md | Catalog Gemini CLI MCP servers | SATISFIED | `collect_gemini_mcp` emits `(none found)` via -s guard on 0-byte file |
| FMT-03 | 03-01-PLAN.md, 03-04-PLAN.md | No secrets written — name + transport only | SATISFIED | Zero hits across all 7 secret patterns + /Users/ path check on live combined output |

**All 10 Phase 3 requirements satisfied.**

No orphaned requirements: REQUIREMENTS.md maps CC-01..03, CDX-01, OC-01..03, GEM-01..02, FMT-03 to Phase 3 — all 10 claimed in PLANs.

---

### Anti-Patterns Found

Scanned all Phase 3 additions (lines 773–1238 of update-list.sh):

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `update-list.sh` | 885 | `name=""` reset added per WR-04 | INFO | Defensive pattern; correct fix, not a bug |

No TBD, FIXME, XXX, or unresolved debt markers found in Phase 3 function bodies.
No placeholder/stub returns. No hardcoded empty data flowing to output.
No `return null` or `return {}` stubs.

---

### Human Verification Required

None. All verifiable behaviors were confirmed programmatically:
- Live collector execution against real machine data
- FMT-03 zero-leakage grep on actual output
- Determinism diff on two consecutive runs
- Syntax check via `zsh -n`
- Code-level audit for secret-field access patterns

---

### Gaps Summary

No gaps. All 10 must-haves are VERIFIED. The four ROADMAP success criteria that describe
"Running update-list.sh produces..." sections are intentionally deferred to Phase 5, which
is explicitly the "Integration & Verification Gates" phase responsible for wiring all
collectors into `generate_catalog`. This is not a gap — it is the designed delivery split:
Phase 3 delivers correct, tested, FMT-03-compliant collector functions; Phase 5 wires them.

---

_Verified: 2026-06-13T17:32:10Z_
_Verifier: Claude (gsd-verifier)_
