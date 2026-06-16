---
phase: 23-retire-zsh-reference
verified: 2026-06-16T16:10:00Z
status: passed
score: 4/4
overrides_applied: 0
---

# Phase 23: Retire the Zsh Reference — Verification Report

**Phase Goal:** update-list.sh, the zsh_parity test suite, and the CI zsh -n gate are gone; the test suite stands on its own with direct collector tests backfilling the lost coverage; README and docs describe maccat as the standalone tool.
**Verified:** 2026-06-16T16:10:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | update-list.sh removed from the repo (ZSH-01) | VERIFIED | `test ! -f update-list.sh` → file absent |
| 2 | zsh_parity test suite and CI zsh -n gate removed (ZSH-02) | VERIFIED | All three test files/dirs absent; `grep -c "zsh -n" ci.yml` = 0 |
| 3 | Coverage backfilled with direct collector tests; full suite passes and ruff + mypy --strict clean (ZSH-03) | VERIFIED | 421 passed, 5 skipped (pyz infra only); no parity/golden/zsh skips; ruff: all checks passed; mypy: no issues in 30 source files |
| 4 | README/docs no longer reference update-list.sh or byte-parity; maccat described as standalone; one history note allowed (ZSH-04) | VERIFIED | `grep -niE "zsh|update-list|parity|--personal|--office|--machine" README.md` returns exactly line 313 (the permitted history note only) |

**Score:** 4/4 truths verified

---

## Requirement-by-Requirement Detail

### ZSH-01: update-list.sh removed

Command: `test ! -f update-list.sh`
Result: PASS — file absent from repo root.

### ZSH-02: Parity suite and CI gate removed

| Check | Command | Result |
|-------|---------|--------|
| test_golden_parity.py absent | `test ! -f tests/test_golden_parity.py` | PASS |
| test_update_list_integrity.py absent | `test ! -f tests/test_update_list_integrity.py` | PASS |
| tests/golden/ absent | `test ! -d tests/golden` | PASS |
| CI zsh -n gate absent | `grep -c "zsh -n" .github/workflows/ci.yml` = 0 | PASS |
| conftest.py clean | No `update_golden`/golden references found | PASS |
| PYTHONHASHSEED matrix retained | `grep -ic "pythonhashseed" ci.yml` = 2 | PASS |
| CI pytest/ruff/mypy gates retained | All three steps present in ci.yml | PASS |

The CI workflow retains the full PYTHONHASHSEED matrix (`[0, 42, "random"]`) and the lint/type/test gates. Only the TEST-04 `zsh -n update-list.sh` step was removed.

### ZSH-03: Coverage backfilled; suite clean

The two new degradation tests added in plan 23-01 both pass:

- `tests/test_helpers.py::TestChromeExtName::test_msg_non_dict_messages_json_degrades_to_ext_id` — exercises `isinstance(messages, dict)` guard in `chrome_name.py:52-53`
- `tests/test_helpers.py::TestResolveVscExtName::test_nls_non_dict_top_level_degrades_to_ext_id` — exercises `isinstance(nls, dict)` guard in `vsc_name.py:53-54`

No dangling imports to deleted scaffold: `grep -rn "tests.golden|test_golden_parity|ZSH_CAPTURABLE|update_golden" tests/` → no results.

Full suite result: **421 passed, 5 skipped** (3.07s). The 5 skips are all `tests/test_pyz.py` with reason "dist/maccat.pyz not built; run scripts/build-pyz.sh first" — pyz infrastructure, unrelated to this phase. Zero parity/golden/zsh skips remain (the 3 Phase-22 parity skips are gone along with the file).

Ruff: `All checks passed!`
Mypy --strict: `Success: no issues found in 30 source files`

### ZSH-04: README docs scrubbed

`grep -niE "zsh|update-list|parity|--personal|--office|--machine" README.md` returns exactly one line:

```
313: maccat was originally implemented as a Zsh script and ported to Python in v1.0.0.
```

This is the single permitted history note. All operational references to the zsh script, byte-parity, and stale flags (`--personal`, `--office`, `--machine`) are absent.

`--computer` flag is documented in four places: usage example (line 107), options table (line 114), Machine Identity section (lines 128, 150).

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `update-list.sh` | DELETED | VERIFIED | Absent from repo root |
| `tests/test_golden_parity.py` | DELETED | VERIFIED | Absent |
| `tests/test_update_list_integrity.py` | DELETED | VERIFIED | Absent |
| `tests/golden/` | DELETED | VERIFIED | Directory absent |
| `tests/test_helpers.py` | Two new degradation tests | VERIFIED | Both methods present at lines 232 and 395; both pass |
| `tests/conftest.py` | No golden/update_golden references | VERIFIED | Clean — only `tmp_json`, `git_repo`, `catalog_repo` fixtures |
| `.github/workflows/ci.yml` | zsh -n step removed; PYTHONHASHSEED + pytest/ruff/mypy retained | VERIFIED | Confirmed by inspection and grep |
| `README.md` | No operational zsh/update-list refs; one history note; --computer documented | VERIFIED | Confirmed by grep |

---

## Anti-Patterns Found

No blockers or build/lint/test failures.

Two info-level items from the code review (REVIEW.md) are acknowledged as out-of-scope tech debt:

| Finding | Severity | Impact | Disposition |
|---------|----------|--------|-------------|
| IN-01: `# (See REVIEW.md CR-01/WR-02)` comments in `chrome_name.py` and `vsc_name.py` point to an unlocatable file | Info | Navigability only; logic is correct and covered by new tests | Out of scope for this phase; no build/test impact |
| IN-02: ~88 `update-list.sh:NNNN` cross-reference comments throughout `src/` and `tests/` now point to deleted file | Info | Navigability only; git history retains the file | Explicitly accepted in 23-CONTEXT.md decisions: "Delete update-list.sh outright, relying on git history if needed"; ZSH-04 scope was limited to operational README/docs references |

Neither item is a BLOCKER. No `TBD`, `FIXME`, or `XXX` markers found in files modified by this phase.

---

## Human Verification Required

None — all phase deliverables are verifiable programmatically via file existence, grep, and test execution.

---

## Gaps Summary

No gaps. All four requirements (ZSH-01 through ZSH-04) are fully satisfied by observable codebase evidence. The phase goal is achieved.

---

_Verified: 2026-06-16T16:10:00Z_
_Verifier: Claude (gsd-verifier)_
