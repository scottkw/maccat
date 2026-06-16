# Phase 23: Retire the zsh Reference - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning
**Mode:** Smart discuss — infrastructure/cleanup phase with ZSH-03/ZSH-04 judgment calls

<domain>
## Phase Boundary

`update-list.sh`, the `zsh_parity` test suite, and the CI `zsh -n` gate are gone.
The test suite stands on its own via direct collector tests (gaps backfilled where
the goldens uniquely covered formatting). README and docs describe maccat as the
standalone tool. maccat is now the sole source of truth — no zsh reference.

Covers: ZSH-01 (remove update-list.sh), ZSH-02 (remove parity suite + CI zsh -n
gate), ZSH-03 (backfill lost coverage), ZSH-04 (scrub docs).
</domain>

<decisions>
## Implementation Decisions

### Delete update-list.sh (ZSH-01)
- Remove `update-list.sh` from the repo outright. Git history retains the full file
  if ever needed. Do NOT move it to docs/legacy.

### Remove the parity suite + CI gate (ZSH-02)
- Delete the entire `tests/golden/` parity scaffold: all `tests/golden/*.golden.txt`
  files, `tests/golden/generate.py`, `tests/golden/normalize.py`, and
  `tests/golden/fixtures/` if it only serves parity.
- Delete `tests/test_golden_parity.py` (both `test_section_parity` static-golden
  cases AND `test_live_zsh_parity`, which sources update-list.sh live).
- Delete `tests/test_update_list_integrity.py` (the `zsh -n` tripwire).
- Remove the CI `zsh -n update-list.sh` step from `.github/workflows/ci.yml`
  (the "Check update-list.sh syntax (TEST-04)" step, ~lines 39-40). Also remove any
  `PYTHONHASHSEED` matrix steps that exist ONLY to exercise parity determinism if they
  no longer serve a purpose — but keep the core pytest/ruff/mypy CI gates.

### Backfill lost coverage (ZSH-03)
- **Key fact:** every collector ALREADY has a direct unit test
  (`tests/collectors/test_*.py` for all 11 collector modules; mas is in
  `test_homebrew.py`, webapps in `test_setapp.py`). The parity suite is a redundant
  secondary layer, NOT the sole coverage.
- Approach: **audit + fill gaps** — review each collector's existing direct test and
  add assertions ONLY where a golden uniquely encoded output formatting the direct
  test currently misses (e.g. exact section header text, `(none found)` empty-state,
  multi-profile dedup ordering, `__MSG_`/nls name resolution, MCP transport-only
  secret-safety). Do NOT rewrite tests wholesale or manufacture redundant cases.
- After deletion, the full suite must remain meaningful and green.

### Scrub docs (ZSH-04)
- Remove all OPERATIONAL references to `update-list.sh` / zsh / byte-parity from
  README and docs; describe maccat as the standalone Python tool.
- KEEP one brief history note (e.g. in README history/changelog or PROJECT context):
  "originally a Zsh script, ported to Python (v1.0.0)". Do not erase the lineage,
  just stop presenting zsh as a live/parallel implementation.

### Claude's Discretion
- Exact gap-fill assertions per collector — Claude's judgment after the audit.
- Whether `tests/conftest.py` needs edits (only if it imports from `tests.golden`).
- Whether any helper test (`test_format.py`, `test_writer.py`) referenced goldens and
  needs adjustment.
- CI workflow edits beyond removing the zsh step — keep CI green and minimal.
</decisions>

<code_context>
## Existing Code Insights

### Files to remove
- `update-list.sh` (repo root).
- `tests/test_golden_parity.py` — `EXPECTED_STEMS`-driven `test_section_parity`
  (static goldens) + `test_live_zsh_parity` (imports `ZSH_CAPTURABLE` from
  `tests/golden/generate.py`, runs update-list.sh live).
- `tests/test_update_list_integrity.py` — `zsh -n update-list.sh` tripwire.
- `tests/golden/` — `*.golden.txt`, `generate.py`, `normalize.py`, `__init__.py`,
  `fixtures/` (verify nothing outside parity imports these before deleting).
- `.github/workflows/ci.yml` — the "Check update-list.sh syntax (TEST-04)" step.

### Import-coupling to check before deleting (so nothing breaks)
- `grep -rn "tests.golden\|test_golden_parity\|update-list\|ZSH_CAPTURABLE\|generate\b\|normalize" tests/ .github/`
  — confirm `conftest.py`, `test_safety_invariants.py`, `test_pyz.py`, `test_format.py`,
  `test_writer.py` do NOT depend on the golden scaffold; if any do, sever the dependency.

### Collectors already covered by direct tests (ZSH-03 baseline)
- `tests/collectors/`: test_chrome, test_claude, test_codex, test_cursor, test_firefox,
  test_gemini, test_homebrew (+ mas), test_opencode, test_setapp (+ webapps), test_vscode.
- Phase 22 added strong direct tests for homebrew/setapp/webapps/plist already.

### Established patterns
- stdlib-only, ruff + `mypy --strict` clean, pytest. Use `./venv/bin/python`.
- The 3 parity cases for homebrew/setapp/web-installed were SKIPPED in Phase 22
  (22-03) pending this phase — they vanish when `test_golden_parity.py` is deleted.
</code_context>

<specifics>
## Specific Ideas

The zsh reference proved the v1.0.0 Python port and has served its purpose; keeping
it frozen blocks every output/CLI change (as Phase 22 demonstrated). Retiring it makes
maccat the standalone canonical tool — the milestone's headline outcome.
</specifics>

<deferred>
## Deferred Ideas

None — this is the final phase of the milestone. Future candidates (restore/reinstall,
diffing, more browsers, PyPI) remain in REQUIREMENTS.md's v2 section, out of scope here.
</deferred>
