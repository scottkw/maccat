---
phase: 17-parity-safety-tests
verified: 2026-06-15T04:37:20Z
status: passed
score: 4/4
overrides_applied: 0
---

# Phase 17: Parity & Safety Tests — Verification Report

**Phase Goal:** The Python implementation is proven byte-identical to the zsh reference for every catalog section, and all three destructive-op safety invariants are covered by isolated-fixture tests.
**Verified:** 2026-06-15T04:37:20Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Golden-output parity tests pass: Python catalog section bodies byte-identical to zsh output after volatile-field normalization; `[id]` preserved, never stripped | VERIFIED | `pytest -m zsh_parity -v`: 13 passed. `normalize_catalog_body` only strips `\d{14}` — confirmed in normalize.py:43. `[id]` fields confirmed present in all non-empty golden files. |
| 2 | update-list.sh present, unmodified, passes `zsh -n` at milestone end | VERIFIED | `zsh -n update-list.sh` → clean. `git diff --quiet HEAD -- update-list.sh` → UNMODIFIED. test_update_list_integrity.py also enforces this in the test suite. |
| 3 | Isolated-fixture tests cover the 3 destructive-op safety invariants: (a) prune skips unparseable; (b) tied-newest kept; (c) rename refuses clobber | VERIFIED | `pytest -m safety_invariant -v`: exactly 3 passed. Prune test uses `mac-software-list-[alpha]-2026.txt` (matches glob, unparseable 4-digit ts) — exercises the real `cf is None` skip branch. |
| 4 | PYTHONHASHSEED=random set in CI; parity tests pass across multiple hash seeds | VERIFIED | CI matrix `pythonhashseed: [0, 42, "random"]` (ci.yml:15). Local run: `PYTHONHASHSEED=0 pytest -q` → 434 passed; `PYTHONHASHSEED=random pytest -q` → 434 passed. |

**Score:** 4/4 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/golden/normalize.py` | normalize_catalog_body, extract_section_body, SEPARATOR_LINE | VERIFIED | Exports all three. CR-01 fixed: only strips `\d{14}`; `[id]` preserved. Separate `normalize_catalog_header()` for filename-scoped substitutions. |
| `tests/golden/generate.py` | ZSH_CAPTURABLE dict, capture_zsh_section, capture_zsh_section_body, regenerate_zsh_goldens | VERIFIED | All present. 13-section `ZSH_CAPTURABLE`, 4-section `NON_ZSH_CAPTURABLE`. `_ZSH_TIMEOUT_SECONDS = 30` named constant (IN-03). |
| `tests/test_golden_parity.py` | test_section_parity (17 parametrized), test_live_zsh_parity (13 parametrized, zsh_parity marker) | VERIFIED | Both tests present and passing. CR-02 fix: goldens are zsh-sourced for the 13 capturable sections. |
| `tests/test_safety_invariants.py` | 3 safety invariant tests with `safety_invariant` marker | VERIFIED | Exactly 3 tests, all marked `pytestmark = pytest.mark.safety_invariant`. All pass. |
| `tests/test_update_list_integrity.py` | test_update_list_passes_zsh_syntax_check (TEST-04) | VERIFIED | Present and passing. Runs `zsh -n update-list.sh` as a pytest test. |
| `tests/conftest.py` | --update-golden addoption + update_golden fixture | VERIFIED | Lines 59-79: addoption and fixture present. Existing fixtures unchanged. |
| `tests/golden/*.golden.txt` (17 files) | Normalized section body goldens for all 17 sections | VERIFIED | Exactly 17 files. No raw 14-digit timestamps. `[id]` fields present in all non-empty sections. All committed (git status clean). |
| `.github/workflows/ci.yml` | macos-latest runner, PYTHONHASHSEED matrix with "random", named TEST-04 step | VERIFIED | `runs-on: macos-latest`. Matrix: `[0, 42, "random"]`. Named step "Check update-list.sh syntax (TEST-04)". |
| `tests/golden/fixtures/fake_home/` | Synthetic HOME tree with data for all 17 section types | VERIFIED | 18 files covering all collectors: Claude, Codex, OpenCode, Gemini, VSCode, Cursor, Chrome, Firefox. Committed. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `test_golden_parity.py` | `tests/golden/normalize.py` | `from tests.golden.normalize import normalize_catalog_body` (line 56) | WIRED | Import at module level; normalize_catalog_body called in both test_section_parity and test_live_zsh_parity. |
| `test_golden_parity.py::test_live_zsh_parity` | `tests/golden/generate.py` | Module-level `from tests.golden.generate import ZSH_CAPTURABLE` (line 379); lazy import of `capture_zsh_section_body` inside test body (lines 403-404) | WIRED | ZSH_CAPTURABLE import at module scope (needed for `@pytest.mark.parametrize`); zsh-executing functions imported lazily inside test body. Import of ZSH_CAPTURABLE alone does not trigger zsh subprocesses (verified: 0.020s import time). |
| `test_golden_parity.py::test_live_zsh_parity` | `update-list.sh` | `capture_zsh_section_body` → `capture_zsh_section` → `subprocess.run(["zsh", "-c", "source update-list.sh; {collector_fn}"])` | WIRED | Live zsh sourcing confirmed: 13 `zsh_parity` tests pass and capture live zsh output. |
| `tests/test_safety_invariants.py` | `maccat.retention.prune_old_archives` | direct import + call with `tmp_path` fixture | WIRED | Exercises real `cf is None` skip branch via glob-matching unparseable filename. |
| `tests/test_safety_invariants.py` | `maccat.retention.retain_newest_per_host` | direct import + call with `tmp_path` fixture | WIRED | Two distinct hosts with identical timestamps both retained. |
| `tests/test_safety_invariants.py` | `maccat.identity.rename_machine` | direct import + call with `tmp_path` + `monkeypatch` | WIRED | `SystemExit` raised on destination-exists clobber. |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| TEST-01 | 17-01-PLAN, 17-02-PLAN | Golden-output parity test suite asserting Python bodies byte-identical to zsh reference | SATISFIED | `test_section_parity` (17 cases) + `test_live_zsh_parity` (13 live cases). All 434 tests pass. |
| TEST-02 | 17-01-PLAN, 17-02-PLAN | Volatile fields normalized; stable fields (item lines, [id], sort order, (none found)) asserted exactly | SATISFIED | `normalize_catalog_body` only strips `\d{14}`; [id] explicitly preserved (CR-01). Golden files committed verbatim (WR-05). |
| TEST-03 | 17-03-PLAN | Isolated-fixture tests for 3 destructive-op safety invariants | SATISFIED | `pytest -m safety_invariant` → 3 passed. All on `tmp_path` fixtures, never real HOME. |
| TEST-04 | 17-03-PLAN | update-list.sh untouched, passes `zsh -n` at milestone end | SATISFIED | `git diff --quiet HEAD -- update-list.sh` → UNMODIFIED. Named CI step "Check update-list.sh syntax (TEST-04)" present. `zsh -n` passes. |

---

## CR-02 Gate-Integrity Resolution

This was the critical gate-integrity fix: the original implementation wrote goldens from Python collector output, making `test_section_parity` assert Python==Python (tautological for TEST-01).

**Fix verified:**

1. `regenerate_zsh_goldens()` in generate.py sources `update-list.sh` in real zsh and writes the zsh-captured BODY as the authoritative golden for each of the 13 ZSH_CAPTURABLE sections. Re-running it produces byte-identical output (confirmed in 17-REVIEW-FIX.md — `git diff` on `*.golden.txt` was empty after re-generation).

2. `test_live_zsh_parity` captures zsh LIVE on every run (not from committed golden), normalizes both sides, and asserts Python == live zsh. A wrong Python `[id]` fails the gate — proven by mutation test (`vscomp.test-ext-WRONG` failed with diff showing the ID mismatch).

3. `NON_ZSH_CAPTURABLE` (homebrew/mas/setapp/webapps) are documented as Python-format goldens with no false zsh-parity claim.

4. The 13 `zsh_parity` tests PASS on this macOS machine (zsh present on PATH) and are not skipped.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite with PYTHONHASHSEED=0 | `PYTHONHASHSEED=0 PYTHONPATH=src ./venv/bin/pytest -q` | 434 passed | PASS |
| Full suite with PYTHONHASHSEED=random | `PYTHONHASHSEED=random PYTHONPATH=src ./venv/bin/pytest -q` | 434 passed | PASS |
| Live zsh-parity tests | `PYTHONPATH=src ./venv/bin/pytest -m zsh_parity -v` | 13 passed, 421 deselected | PASS |
| Safety invariant tests | `PYTHONPATH=src ./venv/bin/pytest -m safety_invariant -v` | 3 passed, 431 deselected | PASS |
| Ruff lint | `./venv/bin/ruff check src tests` | All checks passed | PASS |
| Mypy strict | `./venv/bin/mypy --strict src/maccat` | Success: no issues in 29 source files | PASS |
| update-list.sh syntax | `zsh -n update-list.sh` | Exit 0 (clean) | PASS |
| update-list.sh unmodified | `git diff --quiet HEAD -- update-list.sh` | Clean (UNMODIFIED) | PASS |

---

## Anti-Patterns Found

None. No TBD/FIXME/XXX markers in any of the 7 phase-modified files. No stub implementations. No empty handlers. All golden files contain real content.

**Note (IN-01 from 17-REVIEW.md):** The `test_retain_keeps_all_tied_newest` test covers two different hosts with the same timestamp (per-host independence) but not the same-host tie case. The REVIEW.md flags this as informational (IN-01) and confirms the same-host tie case is covered in `test_retention.py`. This is not a blocker.

**Note on generate.py module-level import:** The PLAN 17-01 must-have states "generate.py is never imported on a normal test run." In the final implementation, `from tests.golden.generate import ZSH_CAPTURABLE` IS imported at module level in test_golden_parity.py (line 379) to supply `@pytest.mark.parametrize` IDs. However, importing this constant does not trigger any zsh subprocess (verified: 0.020s import time). The zsh-executing functions (`capture_zsh_section_body`, `FAKE_HOME`) remain lazily imported inside the test body. The original must-have intent — "golden files are not auto-updated on a normal run" (T-17-03) — is preserved. This deviation was introduced by the CR-02 fix which the REVIEW.md documents as resolved.

---

## Human Verification Required

None. All success criteria are verifiable programmatically and all pass.

---

_Verified: 2026-06-15T04:37:20Z_
_Verifier: Claude (gsd-verifier)_
