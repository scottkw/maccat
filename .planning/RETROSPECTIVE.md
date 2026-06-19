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

## Milestone: v2.0.0 — Standalone maccat — CLI Cleanup & Versioned Catalog

**Shipped:** 2026-06-16
**Phases:** 3 (21-23) | **Plans:** 8

### What Was Built
Collapsed the four folder-selecting flags to a single `--computer NAME` (removed
`--personal`/`--office`/`--machine`); added version numbers to every software section (Homebrew
formulae/casks via `brew list --versions`; Setapp + web-installed `/Applications` via a shared
never-raising `plistlib` helper); and retired the `update-list.sh` zsh reference, the `zsh_parity`
suite, and the CI `zsh -n` gate, leaving direct collector tests as the standalone coverage.

### What Worked
- **The audit gates earned their keep on the meta-work, not just the code.** The plan-checker
  rejected a 23-01 plan whose entire premise was false (it would have duplicated existing helper
  tests) — caught before any code was written. Code review caught a Critical never-raises violation
  in the new plist helper (array-root `Info.plist` → `AttributeError`) that the unit tests missed.
- **Crash recovery without a worktree.** A sequential executor died mid-plan (API socket close) in
  22-01 having committed task 1 + written task-3 tests but not the task-2 impl. Inspecting the
  partial git/disk state and finishing the impl by hand was faster and safer than re-dispatching.
- **Sequencing the parity retirement correctly.** Phase 22 only *skipped* the 3 invalidated parity
  cases (no tautological golden regeneration); Phase 23 deleted the whole scaffold — keeping each
  phase's gate honest and green.

### What Was Inefficient
- The planner twice wrote on stale assumptions about existing tests (23-01 false premise), costing a
  plan-check + re-plan cycle. A quick `ls tests/` baseline in the planner prompt would have avoided it.
- `milestone.complete` auto-extracted garbage accomplishments ("One-liner:") because SUMMARY files
  lacked a clean one-liner field — required a manual MILESTONES.md rewrite.

### Patterns Established
- For deletion/retirement phases: backfill coverage in an earlier wave, delete in a later wave, so
  coverage is never momentarily lost (Wave 1 backfill → Wave 2 delete).
- Never regenerate parity goldens from the new implementation's own output — skip + reason, then
  delete the scaffold in a dedicated phase.

### Key Lessons
- "Backfill lost coverage" is an *audit* task first, not a *write* task — most of the coverage often
  already exists; find the true gap before generating tests.
- A never-raising helper must wrap every syscall (incl. `stat()`) AND guard the parsed shape
  (`isinstance(data, dict)`) — partial try-blocks leak exceptions on valid-but-wrong-shape input.

### Cost Observations
- Model mix: Opus orchestration; Sonnet subagents throughout.
- Notable: one executor API-crash recovered inline; two plan-check/re-plan cycles (one real BLOCKER).

## Milestone: v2.1.0 — Reinstall from Catalog

**Shipped:** 2026-06-16
**Phases:** 3 (24-26) | **Plans:** 4

### What Was Built
The catalog→restore loop: `MasCollector` preserves the App Store ID (MAS-01); `reinstall/parser.py`
parses a catalog back into a typed `ParsedCatalog` round-trip-locked to `emit_item` (PARSE-01);
`reinstall/emitter.py` renders an injection-safe, idempotent, `bash -n`-clean `reinstall.sh`
(GEN-01..04, MAN-01); and `maccat reinstall [--from PATH | --computer NAME]` wires it into the CLI
via a surgical two-point dispatch that leaves the 13-step gen path untouched (RST-01/02).

### What Worked
- Coarse 3-phase split with a hard dependency order (format/parser → emitter → CLI) kept each phase
  small and the contracts clean; the round-trip contract test made the parser↔emitter coupling safe.
- The code-review + auto-fix loop earned its cost: it caught a genuine `set -Eeuo pipefail` BLOCKER
  (bare `mas install` aborting the whole script on a routine non-zero) that all 62 unit tests missed
  because they only ran `bash -n`, never executed the script under `set -e`.
- Grounding discuss/research in the real code surfaced two load-bearing facts early: Homebrew is one
  merged formulae+casks section (→ universal guard), and `--computer` was top-level-only (→ WR-03).

### What Was Inefficient
- Worktree executors repeatedly forked from a base predating recent main commits and, in one case, ran
  `pip install -e .` inside the worktree — repointing the shared venv `.pth` and breaking `import
  maccat` repo-wide after cleanup. Cost a diagnosis cycle; now captured as a memory + an explicit
  "do not reinstall editable in a worktree; run via PYTHONPATH=src" instruction to executors.
- The review's first suggested CR-01 fix (`A && B && install`) was itself unsafe under `set -e`
  (final command not exempt); only the new runtime-execution tests caught it — a reminder that
  syntax-only test coverage gives false confidence on shell-safety claims.

### Patterns Established
- **Runtime-execution tests for generated shell scripts** — stub tools on a temp PATH, run the script
  under `bash -Eeuo pipefail`, assert it does not abort mid-run; mutation-verify the guard.
- **Two-point CLI dispatch** — split an argparse step to satisfy conflicting preconditions (`--from`
  needs no repo; the picker does) while keeping the legacy path byte-untouched.
- **`quote_for_script()` + `safe_comment_value()`** — a single shell-interpolation chokepoint, plus a
  separate newline-strip for comment context (shlex.quote does not make comments safe).

### Key Lessons
- A "guard line" success criterion must be runtime-verified, not just present in the emitted text.
- Shared dev-venv state (editable `.pth`) is global mutable state across worktrees — treat accordingly.

### Cost Observations
- Model mix: Opus orchestration; Sonnet subagents throughout (researcher/planner/checker/executor/
  reviewer/fixer/verifier). Fully autonomous discuss→plan→execute per phase.
- Notable: 3 code-review auto-fix loops (one converged after fixing a real BLOCKER + a review
  self-correction); one venv-pollution diagnosis cycle; zero human interventions beyond grey-area
  acceptance.

## Milestone: v2.2.0 — Broader Coverage

**Shipped:** 2026-06-17
**Phases:** 3 (27-29) | **Plans:** 5

### What Was Built
Five new catalog sections, all additive and stdlib-only, taking the catalog from 17 to 22 sections
(16 collectors). A new `ChromiumBaseCollector` (`collectors/chromium.py`) factors out the shared
profile-walk, `__MSG_`/`_locales` name resolution, and component-denylist filter; `ChromeCollector`
becomes a thin subclass (left byte-identical), and `EdgeCollector` (BRW-01) + `BraveCollector`
(BRW-02) join it with per-browser denylists. `ZedCollector` (BRW-03) reads `Zed/extensions/index.json`
filtering `dev` entries; `SafariCollector` (BRW-04) shells to `pluginkit -p com.apple.Safari.web-extension`
and reads each `.appex` `Info.plist`, every step never-raising; `CodexCollector` gains a second
identity-only "Codex Plugins" section (CDX-02). All five fall through the unchanged reinstall pipeline
to the manual checklist (zero `reinstall/` changes).

### What Worked
- The rule-of-three paid off: with Chrome + Edge + Brave as three real Chromium examples, extracting
  `ChromiumBaseCollector` was a clean abstraction rather than speculation, and retargeting the existing
  `test_chrome.py` patches to the base proved Chrome stayed byte-identical.
- Coarse phase ordering by risk (independent low-risk Codex/Zed first, the shared-collector refactor
  in the middle, highest-failure-mode Safari last and isolated) meant the riskiest work could have
  been deferred without blocking anything before it.
- The live `pluginkit` smoke test (Bitwarden) gated the Safari phase against an undocumented tool whose
  output format isn't guaranteed stable — static review alone would not have validated the parse.
- The code-review + auto-fix loop again earned its cost: caught two never-raising gaps (codex subprocess
  `OSError`, Zed non-object JSON) and a wrong Safari name-fallback chain.

### What Was Inefficient
- A Phase 29 executor worktree forked from a base predating Phases 27/28 and would have clobbered the
  canonical 27/28 files on merge; caught only during merge inspection, and the Safari work had to be
  reconstructed surgically on main. The recurring worktree-staleness failure mode (see v2.1.0) bit again
  in a more dangerous form — near data-loss rather than just a venv repoint.
- A mid-run `gsd-sdk` npx-cache eviction interrupted the flow and required reinstalling GSD (1.42.3)
  before continuing — external-toolchain fragility, not a project defect, but a real cost.

### Patterns Established
- **Rule-of-three abstraction with byte-parity proof** — extract a base only when a third real example
  exists, and prove the incumbent subclass is unchanged by retargeting its existing tests at the base.
- **Live smoke test as a phase gate for undocumented external tools** — when output format isn't
  contractually stable (`pluginkit`), validate against real output before closing the phase.
- **Identity-only collection for secret-bearing sources** — Codex plugins emit name + id only and never
  read plugin bundle files, extending the FMT-03 discipline to a new source.

### Key Lessons
- Worktree base-staleness is now a repeat offender across two milestones; merge inspection caught a
  near-clobber this time, but the pattern needs a guard (verify the worktree base is current before
  trusting a merge), not just vigilance.
- A shared-collector refactor is only safe to call "no behavior change" when the incumbent's own tests
  run green against the refactored base — assertion, not assumption.

### Cost Observations
- Model mix: Opus orchestration; Sonnet subagents throughout. Largely autonomous discuss→plan→execute
  per phase.
- Notable: 3 per-phase code-review auto-fix loops (converged clean); one stale-worktree near-clobber
  recovery (surgical reconstruction on main); one `gsd-sdk` npx-cache reinstall. 628 tests green;
  ruff + mypy --strict clean.

## Milestone: v3.0.0 — Markdown Catalog Format

**Shipped:** 2026-06-19
**Phases:** 3 (30-32) | **Plans:** 7

### What Was Built
A breaking catalog format change from plain-text to rendered markdown. A shared emitter
(`catalog/markdown.py::render_markdown_catalog`) renders double-quoted YAML frontmatter +
per-section `Name | Version | ID` tables; `.txt`→`.md` moved across the filename pattern,
retention/archive globs, git staging, and the reinstall picker. `parse_markdown_catalog`
(`reinstall/parser.py`) inverts the emitter and the round-trip was re-locked by a contract test;
`maccat reinstall` now consumes `.md` only, refusing legacy `.txt` and frontmatter-less `.md`
(extension + content-sniff) with a `convert` directive. New `maccat convert --from PATH` upgrades a
legacy `.txt` in place (atomic write-then-unlink, single commit). The legacy `parse_catalog` was
retained as the convert reader. `__version__` bumped 2.1.0 → 3.0.0 at release.

### What Worked
- **The recurring stale-worktree failure mode was finally caught structurally, not by vigilance.**
  In v2.1.0 it caused a venv repoint; in v2.2.0 a near-clobber caught only at merge. This milestone,
  both Phase 32 executors forked from a stale base (`d58f381`, pre-Phase 30) — and the executor's
  own HEAD-assertion + base-correction preamble detected it and `git reset --hard`'d to the correct
  base before doing any work. The guard the v2.2.0 retro asked for did its job twice.
- Adversarial code review again paid for itself with a genuine blocker: a YAML frontmatter injection
  in the Phase 30 emitter (unquoted `computer`/`hostname` → invalid YAML on any colon-containing
  value) that the phase verifier missed because it only tested clean inputs — and which would have
  broken the Phase 31 round-trip in production. Caught and fixed (double-quote all scalars) before
  Phase 31 was even planned.
- The blocking-anti-pattern handoff worked: the worktree editable-`.pth` pollution diagnosed in
  v2.1.0 was carried as a `.continue-here.md` blocking constraint and enforced as a `pip install -e .`
  step before every post-merge test gate — no collection-error reruns this milestone.
- One executor (31-01) recognized that its plan's `.txt`-refusal contract couldn't be tested without
  also doing 31-02's CLI wiring, and completed both via Rule-2 deviations — the orchestrator verified
  31-02's acceptance criteria directly rather than re-dispatching over committed work.

### What Was Inefficient
- The local stale `dist/maccat.pyz` (a gitignored CI/release artifact) failed a version-match test
  after the `__version__` bump, prompting an unnecessary local rebuild — CI builds the `.pyz` in a
  separate step *after* pytest, so those tests skip in CI and the bump never threatened it. A few
  minutes spent before recognizing the artifact was irrelevant to the release.
- The milestone-complete CLI auto-extracted placeholder "One-liner:" accomplishments from SUMMARYs
  that lacked a clean one-liner field; the MILESTONES.md entry had to be rewritten by hand.

### Patterns Established
- **Synthesize-from-current-machine for format upgrades** — convert stamps the conversion's own
  context (now() + current hostname) into frontmatter while preserving the original filename
  timestamp; the deliberate filename-ts ≠ frontmatter-generated split is documented so it isn't
  "fixed" later.
- **Two-parser coexistence** — a legacy reader (`parse_catalog`, for convert input) and a new reader
  (`parse_markdown_catalog`, for reinstall) live in one module without conflation, each enforcing its
  own extension contract.

### Key Lessons
- A phase verifier that tests only well-formed inputs will pass a format emitter that breaks on
  adversarial-but-legal values (colons, non-UTF-8 bytes); the adversarial code-review pass is the net
  that catches what goal-backward verification on happy-path fixtures does not.
- Know which artifacts the release pipeline owns. A local gitignored build artifact should not gate a
  source-level change — let CI build it.

### Cost Observations
- Model mix: Opus orchestration; Sonnet subagents (researcher/planner/checker/executor/reviewer/
  verifier) throughout. Largely autonomous discuss→plan→execute per phase, with user input on
  smart-discuss grey areas and the release version/tag decision.
- Notable: 3 per-phase code-review auto-fix loops (1 blocker + 7 warnings total, all fixed +
  regression-tested); stale-worktree base auto-corrected twice by the executor guard. 702 tests green;
  ruff + mypy --strict clean.

## Cross-Milestone Trends

| Milestone | Phases | Plans | Verification | Notable |
|-----------|--------|-------|--------------|---------|
| v0.46.0 | 5 | 12 | 5/5 passed | First extension-cataloging milestone; FMT-03/FMT-04 gates green |
| v0.47.0 | 1 | 1 | 1/1 passed | Single coarse phase; data-loss-safety code review; recovered from a mid-task subagent crash |
| v0.48.0 | 3 | 3 | 3/3 passed | Identity + retention controls; code review caught a dead validation regex + a corrupt-commit bug; established destructive-CLI verification discipline |
| v0.49.0 | 3 | 5 | 3/3 passed | Folder-as-identity model; live pty UAT in a disposable clone found & fixed 4 real zsh defects all static gates had passed |
| v1.0.0 | 5 | 21 | 5/5 passed | Byte-parity Python port; adversarial review caught a tautological parity gate + ID-erasing normalization; live zsh_parity suite; zsh reference untouched |
| v1.1.0 | 3 | 6 | 3/3 passed | Extracted code to a public repo from fresh history; CI `.pyz` build + tag-Release; human checkpoint caught a private-host leak the plan missed |
| v2.0.0 | 3 | 8 | 3/3 passed | Single `--computer` flag; versioned catalog; retired the zsh reference + parity gate; plan-checker killed a false-premise plan; review caught a Critical never-raises bug; recovered from an executor API crash |
| v2.1.0 | 3 | 4 | 3/3 passed | `maccat reinstall` (catalog→reviewable reinstall.sh); review caught a real `set -Eeuo pipefail` BLOCKER unit tests missed + a broken `--computer` flag; runtime-execution tests + two-point dispatch established; worktree editable-`.pth` pollution diagnosed & captured |
| v2.2.0 | 3 | 5 | 3/3 passed | 5 new sections (Edge/Brave/Zed/Safari + Codex plugins), 17→22 sections; rule-of-three `ChromiumBaseCollector` extraction with Chrome byte-parity; live `pluginkit` smoke test gated Safari; stale-worktree near-clobber caught at merge & reconstructed on main; `gsd-sdk` npx-cache eviction recovered |
| v3.0.0 | 3 | 7 | 3/3 passed | Breaking `.txt`→`.md` markdown catalog format; shared emitter + re-locked reinstall round-trip + `convert` command; review caught a frontmatter YAML-injection blocker the verifier's happy-path fixtures missed; the stale-worktree base failure mode was finally auto-corrected by the executor's HEAD-assertion guard (twice); `__version__`→3.0.0 |
