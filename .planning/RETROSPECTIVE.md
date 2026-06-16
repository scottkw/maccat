# Project Retrospective

## Milestone: v0.46.0 — Extension Cataloging

**Shipped:** 2026-06-13
**Phases:** 5 | **Plans:** 12 | **Tasks:** 14

### What Was Built
A single `./update-list.sh` run now catalogs, in addition to the existing Homebrew/App Store/Setapp/web-installed software, 13 new sections covering the plugins, MCP servers, and skills/agents of four AI coding CLIs (Claude Code, Codex, OpenCode, Gemini), the extensions of two editors (VS Code, Cursor), and the extensions of two browsers (Chrome, Firefox) across all profiles. All built on a shared dependency-free Zsh helper layer, secret-clean and deterministic.

### What Worked
- **Helper-foundation-first sequencing.** Building `json_get`/`chrome_ext_name`/`emit_item`/`flush_section` in Phase 1 meant every later collector was a thin, uniform consumer — FMT-01/FMT-04 held by construction across all 13 collectors.
- **Research grounded against the real machine.** Every phase's research verified config shapes and ran extractions against this machine's actual tooling/browsers, catching ROADMAP assumptions that were wrong (Gemini MCP path, OpenCode agents-in-a-dir, Codex TOML, python3-vs-plutil) before planning.
- **Per-phase ephemeral self-tests + a final real-catalog gate.** Each collector phase proved itself in isolation; Phase 5 proved the integrated whole. The secret-leakage and determinism gates were exercised on real output, not just asserted.
- **Code review caught a real security bug.** The Phase 1 `json_get` empty-key → full-JSON-dump blocker was found and fixed before any MCP collector could leak via it.

### What Was Inefficient
- SUMMARY `requirements-completed` frontmatter was inconsistently populated (implementation plans left it empty; IDs landed on self-test/integration SUMMARYs), which made the milestone-audit cross-reference noisier than necessary.
- The `audit-open` scanner flagged the CONTEXT.md `<research_flags>` headings as "open context questions" even though every flag was resolved in RESEARCH.md — a false-positive that required manual acknowledgement at close.

### Patterns Established
- **Collector contract:** `write_section` → `_section_lines=()` → loop `emit_item` → `flush_section`. Defensive buffer reset at the top of every collector.
- **FMT-03 secret boundary:** MCP collectors read only the server name + `.type` transport; never env/headers/args/command/url. Transport clamped to a `stdio|http|sse` whitelist.
- **Verification gates scoped to new sections** (via `awk '/^Claude Code Plugins$/,0'`) to avoid false positives from legitimate pre-existing content (Homebrew `libnghttp2`/`httpie`).
- **macOS dependency-free JSON:** `jq → plutil → grep` (never `python3`, which is a blocking xcrun stub on clean macOS).

### Key Lessons
- Verify the runtime landscape before trusting roadmap-level assumptions about file paths and available tools — several proved wrong and would have caused silent failures or hangs.
- A literal verification criterion ("grep the catalog for `http`") can be wrong; reconcile the success criterion to the gate's actual intent (secret leakage in new sections) rather than implementing a false-positive-prone check.

### Cost Observations
- Model mix: orchestration on Opus; all subagents (research/plan/checker/executor/reviewer/fixer/verifier) on Sonnet.
- Sessions: 1 (single-day autonomous run, ~67 commits).
- Notable: per-phase research + adversarial code review materially improved quality (one security blocker + ~10 warnings fixed before close) at modest extra subagent cost.

## Milestone: v0.47.0 — Catalog Retention & Sync

**Shipped:** 2026-06-14
**Phases:** 1 | **Plans:** 1

### What Was Built
Reworked `update-list.sh`'s archive/retention/git logic: each run keeps only the newest catalog per machine in the targeted main folder, archives older per-machine catalogs, hard-deletes archive entries older than 30 days, and stages all changes (adds/moves/deletes) in one git commit so machines converge.

### What Worked
- **Front-loading the design decisions into `/gsd-new-milestone`.** The three behavior-defining choices (per-machine vs single, target-only vs both, hard-delete + git rm) were settled during milestone questioning, so smart-discuss only had to confirm implementation mechanics — discuss was fast and the plan was unambiguous.
- **Research grounded in the existing code + live data.** Reading the actual `archive_old_catalogs` function and running the candidate algorithm against the real filenames caught a latent ordering bug (the old archive call ran before the catalog was even generated) and confirmed `git add -A` scoping before any code was written.
- **Code review on destructive operations.** A focused data-loss review verified `rm`/`mv` can't escape the target archive dir and the newest-per-host is never deleted — exactly where the risk lived.
- **Single coarse phase was the right call.** All six requirements touch the same archive/git code paths and share one end-to-end verification; the plan-checker agreed splitting would only add artificial checkpoints.

### What Was Inefficient
- The code-fixer subagent died mid-task on a socket error after writing a recovery file but before editing the code; the orchestrator had to detect the no-op (via git status + grep) and apply the 3 warning fixes inline. Worth spot-checking agent results against disk rather than trusting the return.
- SUMMARY `requirements-completed` frontmatter was left empty again (same as v0.46.0) — the audit cross-reference leaned on VERIFICATION + traceability instead.

### Patterns Established
- For destructive file operations: operate only on a strict name pattern, never delete on ambiguity (unparseable timestamp, tied-newest), scope `git add -A` to a single subdirectory, and prove safety + idempotence with a synthetic `/tmp` fixture rather than the real tree.
- For brownfield logic changes: read the actual function and main-block call order first; reordering existing calls is often part of the fix.

### Key Lessons
- Verify subagent work against the filesystem — a clean-looking failure (socket drop) can leave zero changes applied despite many tool calls.
- "Most recent" is ambiguous on a multi-machine shared repo; resolving it to "per hostname" up front avoided two machines churning each other's catalogs.

### Cost Observations
- Model mix: Opus orchestration; Sonnet subagents (research/plan/checker/executor/reviewer/verifier).
- Sessions: continued from the v0.46.0 session.
- Notable: one subagent API failure required inline recovery — cheap because the change set was small and verifiable.

## Milestone: v0.48.0 — Machine Identity & Retention Control

**Shipped:** 2026-06-14
**Phases:** 3 | **Plans:** 3

### What Was Built
`--archive-days N` flag (or TTY-guarded prompt, default 30) makes archive retention configurable with fail-fast integer validation before any prune. Catalogs are named with a user-chosen friendly label resolved from `--machine`, a committed `machine-labels.tsv` hostname→label map, or a numbered "create new" menu — auto-resolved per machine after the first run. A `--rename` mode rewrites a label across all of a machine's files in `personal/`, `personal/archive/`, `office/`, and `office/archive/`, updates the map, and stages everything in one commit; OLD-label candidates come from the map ∪ filename segments so the two pre-existing cryptic-hostname machines are renamable.

### What Worked
- Coarse 3-phase split (ARC independent; MID establishes the map+label convention; REN builds on it) kept each phase a single tightly-coupled file change with one plan each — no false parallelism.
- Smart-discuss batch tables (3-4 grey areas accepted at once) front-loaded every design decision before planning, so planner/executor never had to guess.
- Reusing Phase 8's `validate_machine_label` and the atomic `.tmp`+`mv` map-write pattern in Phase 9 kept the shared TSV contract consistent; an inline integration read confirmed the `[...]` parse idiom is identical across rename + retention + prune.

### What Was Inefficient
- The `update-list.sh` script is destructive to run (prune hard-deletes archives; `--rename` moves files + commits), yet both my own behavior tests AND the gsd-verifier agent ran it for "confirmation," each polluting the working tree with dozens of deleted/created catalogs that needed full restores. Cost: three working-tree restorations. Fix adopted mid-milestone: explicit "do NOT run the script; verify via source + `zsh -n` + throwaway `mktemp -d` fixtures" instructions in every executor/verifier/reviewer prompt, and a saved memory.
- One integration-checker subagent died on a transient API socket error after ~30 min; recovered by doing the cross-phase integration check inline (cheap because I already had full context).

### Patterns Established
- Destructive-CLI verification discipline: never run the tool to verify; assert on source, syntax, and isolated fixtures.
- The committed `machine-labels.tsv` is the tool's first self-state file and the shared data source for both label resolution and rename enumeration.

### Key Lessons
- Code review earned its keep this milestone: it caught a **broken zsh label-validation regex** (`[[ =~ [/\[\]] ]]` rejects nothing — the phase's entire input-sanitization contract was dead) and a **`git add -A personal/ office/` exit-128 abort** that would have committed a map update with unstaged renames (corrupt state). Both were real, not stylistic.
- Pre-existing working-tree state (20 intentional `personal/` deletions) must be captured up front so post-pollution restores return to the *user's* state, not just HEAD.

### Cost Observations
- Model mix: Opus orchestration; Sonnet subagents (plan/checker/executor/reviewer/fixer/verifier).
- Sessions: continued from the v0.47.0 session.
- Notable: code-review→fix→re-review loops found and fixed 1 blocker + 2 criticals + 10 warnings across the three phases; all converged to clean in one fix iteration each.

## Milestone: v0.49.0 — Computer-Folder Model

**Shipped:** 2026-06-14
**Phases:** 3 | **Plans:** 5

### What Was Built
The folder name became the computer identity: catalog filenames carry `[folder]`, an always-shown `select_computer` menu (discovery + create-new + Quit + remembered default) replaced silent auto-resolution, `--computer`/alias flags select-or-create non-interactively, and `--rename` was reworked to rename a folder (+ archive) with an opt-out-gated catalog rewrite and a single-commit map update. The separate machine-label system collapsed into the folder identity.

### What Worked
- Spec-driven smart-discuss (the approved design doc was the source of truth) kept all four discuss rounds to fast "accept-all" batches.
- Sequential (no-worktree) execution for same-file, dependency-chained plans avoided the known worktree base-drift regression entirely.
- The code-review→fix→re-review loop converged each phase to clean in one iteration.

### What Was Inefficient
- Static review + isolated function-tests (grep/source/`zsh -n`) passed all gates yet missed three real zsh runtime bugs. Only a live pty-driven run surfaced them — a reminder that destructive-CLI quality needs an actual execution, not just source assertions.
- Pinning the spurious `f=` menu output took an extended bisect (markers + xtrace) because the emitter was a language quirk, not an `echo`.

### Patterns Established
- **Live UAT in a disposable clone with no remote, driven through a Python pty** — the safe way to exercise a destructive interactive CLI end-to-end.
- Prefer `local x=""` (assignment) over bare `local x` inside loops in zsh; use `: >` not `>` to truncate; always `git add -- <pathspec>`.

### Key Lessons
- For a destructive tool, "all gates green" ≠ "works" — schedule a real-run UAT before milestone close.
- A bug found at UAT often spans more than the phase under test: the `local`-echo and `git add` fixes also corrected Phase 11 / the normal-run commit path.

### Cost Observations
- Model mix: Opus orchestration; Sonnet subagents (pattern-mapper/planner/checker/executor/reviewer/fixer/verifier/integration).
- Notable: 4 UAT-discovered defects fixed post-verification; the orchestrator also fixed 2 related latent bugs (upsert `NULLCMD`, normal-path `git add --`) for consistency.

## Milestone: v1.0.0 — Python Port & Distribution

**Shipped:** 2026-06-14
**Phases:** 5 | **Plans:** 21

### What Was Built
A complete, stdlib-only Python port (`maccat`, `src/maccat/`, 3,513 LOC) of the ~2,470-line zsh
`update-list.sh` at byte-for-byte output parity: the output-format layer (`CatalogWriter`,
`emit_item`/`flush_section` via `LC_ALL=C sort`), config/identity/retention (XDG config with
flag>env>file precedence, computer-folder menu, two-pass retention, atomic `machine-labels.tsv`,
refuse-clobber rename), all 12 source collectors (with CAT-05 MCP secret-safety), the end-to-end
CLI + git integration, and a single-file `.pyz` zipapp. Proven by a live `zsh_parity` suite (13
sections asserted Python==zsh at test time, IDs included), a 3-invariant safety suite, and macOS CI
across `PYTHONHASHSEED` 0/42/random. 434 tests; the zsh reference stayed byte-unmodified (TEST-04).

### What Worked
- Treating each port phase as parity-determined kept design churn near zero — the zsh source +
  research were the spec; smart-discuss was skipped for infra phases and used only where genuinely
  new surface existed (Phase 14 config env-var/schema decisions).
- Sequential-on-main-tree execution (shared gitignored venv) avoided the worktree/venv-absence trap.
- Per-phase adversarial code review + re-review loops paid off repeatedly: caught data-loss-on-prune
  (lexicographic vs numeric), non-atomic TSV writes, AttributeError-on-malformed-JSON degradation
  gaps, and CLI corrupt-config crashes.

### What Was Inefficient
- Two provider-quota interruptions stalled the Phase-15 planner mid-run; recovered by checkpointing
  partial plans and resuming with a continuation planner.
- The largest phase (15, 12 collectors / 28 files) needed a two-pass plan because the first planner
  run was cut off at 3 of 8 plans.

### Patterns Established
- Lazy `get_registry()` (imports inside the function) so a section-order registry can reference
  not-yet-built collector modules without breaking incremental per-plan execution.
- Live-reference parity testing (capture the reference implementation at test time and assert
  equality) is stronger than committed golden snapshots — committed goldens silently absorbed
  Python regressions until the gate was switched to live zsh capture.

### Key Lessons
- **An acceptance gate can be hollow.** Phase 17's golden parity initially compared Python-to-Python
  (goldens written from Python output) and a normalization regex erased the very `[id]` field it was
  meant to assert. Adversarial review + an orchestrator-driven empirical zsh-vs-golden diff caught
  both; the fix added a mutation-proven live `zsh_parity` assertion. Always verify the gate has teeth.
- A success criterion stated literally ("PYTHONHASHSEED=random in CI") should not be silently
  reinterpreted (fixed seeds) — the plan-checker flagged it; resolved with a `[0, 42, "random"]` matrix.

### Cost Observations
- Model mix: Opus orchestration; Sonnet subagents (researcher/pattern-mapper/planner/checker/executor/reviewer/fixer/verifier/integration).
- Notable: every phase ran review→fix→re-review (often to a 3rd iteration); the highest-value catches were on destructive/parity paths, not happy-path logic.

## Cross-Milestone Trends

| Milestone | Phases | Plans | Verification | Notable |
|-----------|--------|-------|--------------|---------|
| v0.46.0 | 5 | 12 | 5/5 passed | First extension-cataloging milestone; FMT-03/FMT-04 gates green |
| v0.47.0 | 1 | 1 | 1/1 passed | Single coarse phase; data-loss-safety code review; recovered from a mid-task subagent crash |
| v0.48.0 | 3 | 3 | 3/3 passed | Identity + retention controls; code review caught a dead validation regex + a corrupt-commit bug; established destructive-CLI verification discipline |
| v0.49.0 | 3 | 5 | 3/3 passed | Folder-as-identity model; live pty UAT in a disposable clone found & fixed 4 real zsh defects all static gates had passed |
| v1.0.0 | 5 | 21 | 5/5 passed | Byte-parity Python port; adversarial review caught a tautological parity gate + ID-erasing normalization; live zsh_parity suite; zsh reference untouched |
