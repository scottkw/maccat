---
phase: 03-ai-cli-collectors
fixed_at: 2026-06-13T18:30:00Z
review_path: .planning/phases/03-ai-cli-collectors/03-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-06-13T18:30:00Z
**Source review:** .planning/phases/03-ai-cli-collectors/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7
- Fixed: 7
- Skipped: 0

## Fixed Issues

### WR-01 + IN-03: `collect_codex_mcp` — flush/return placement and TOML comment stripping

**Files modified:** `update-list.sh`
**Commit:** a3b60a4
**Applied fix:**
- WR-01: Moved `flush_section; return` from outside the `if command -v jq` block to INSIDE it, so jq-processed results flush and return while the jq-absent path falls through to the TOML grep fallback. The comment "plutil can't parse CLI JSON inline; fall through to TOML" now matches the actual code behavior.
- IN-03: Added `sed 's/[[:space:]]*#.*$//'` as the first stage in the TOML pipeline, stripping trailing inline comments from section header lines before the name-extraction sed pattern. TOML headers like `[mcp_servers.foo] # desc` now parse correctly.

---

### WR-02: `collect_opencode_plugins` — guard raw path/URL entries missing '@' separator

**Files modified:** `update-list.sh`
**Commit:** 6e14409
**Applied fix:** After `name="${entry%%@*}"`, added a guard that checks if `name == entry` (no `@` found) AND the entry contains `/` (indicating a filesystem path or URL). Such entries emit a WARNING to stderr and are skipped rather than having the full path written into the catalog. Bare plugin names with no `/` (normal token names) pass through unchanged. Guard applied identically in both the jq path and the plutil fallback path.

---

### WR-03: `collect_opencode_mcp` — consolidate double plutil call

**Files modified:** `update-list.sh`
**Commit:** 9b262c4
**Applied fix:** Replaced the two-call pattern (first `plutil -extract "mcp" raw` as a null sentinel, second identical call to enumerate server names) with a single call that reads directly into a `server_names` array. The null/absent check is now `${#server_names[@]} -eq 0`, which also correctly handles the edge case where `.mcp` is a non-object primitive (its value would be a single non-empty string, not a valid server name object, and `plutil -extract "mcp.<value>.type"` would exit 1 setting transport to "stdio" — still safe, but avoided entirely by the architectural fix).

---

### WR-04 + IN-01: `collect_claude_skills_agents` — reset name at loop start; hoist setopt

**Files modified:** `update-list.sh`
**Commit:** 39cbb1e
**Applied fix:**
- WR-04: Added `name=""` at the TOP of each skills loop iteration body (before the `local skill_md=` line) so the variable is unambiguously cleared on every entry regardless of future early-continue guards. The end-of-iteration `name=""` is preserved for symmetry with the agents loop.
- IN-01: Removed the duplicate `setopt local_options null_glob` inside the agents `if` block. A single call is now hoisted above both loops at the function level — once set with `local_options`, null_glob is active for the entire function's execution. The second call was a no-op.

---

### IN-02: `collect_claude_plugins` — move `local ver` to function preamble

**Files modified:** `update-list.sh`
**Commit:** 2c90539
**Applied fix:** Moved `ver=""` from a `local ver=""` declaration inside the plutil fallback `while` loop body to the function preamble alongside `local name="" version="" key=""`. The in-loop occurrence is now a plain assignment `ver=""` (reset before each plutil call), matching project convention that all function-scoped locals are declared at the top of the function.

---

## Verification

**`zsh -n update-list.sh`:** PASS (exits 0 after all fixes)

**Live sanity checks (sourced collectors against this machine):**

| Collector | Expected | Actual | Status |
|-----------|----------|--------|--------|
| `collect_codex_mcp` | (none found) | (none found) | PASS |
| `collect_opencode_plugins` | superpowers | superpowers | PASS |
| `collect_opencode_mcp` | (none found) | (none found) | PASS |
| `collect_claude_skills_agents` | ~103 items | 103 items | PASS |

**FMT-03 zero-leakage check:** grep for `http|token|Bearer|key=|Authorization|sk-|ghp_|/Users/|env` across all MCP collector output → **0 hits**. FMT-03 status: PASS (unchanged from review).

---

_Fixed: 2026-06-13T18:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
