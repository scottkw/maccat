---
plan: 22-03
phase: 22
title: Skip 3 invalidated zsh_parity golden cases (phase gate)
status: complete
requirements: [VER-05, VER-06]
depends_on: [22-01, 22-02]

dependency_graph:
  requires:
    - 22-01  # homebrew versioned output
    - 22-02  # setapp + webapps versioned output
  provides:
    - green-pytest-gate-phase-22
  affects:
    - tests/test_golden_parity.py

tech_stack:
  added: []
  patterns:
    - pytest.skip() inside parametrized test body for conditional per-stem skips

key_files:
  modified:
    - tests/test_golden_parity.py

decisions:
  - "Skip homebrew-packages, setapp-applications, web-installed-applications parity cases at runtime using pytest.skip() inside test_section_parity; the XFAIL_STEMS dict carries the reason strings referencing ZSH-02 / Phase 23."
  - "Goldens left untouched (anti-tautology rule: do not regenerate from Python output)."
  - "Exactly 3 new skips added; 5 pre-existing skips unaffected; 14 parity cases remain PASSED."

metrics:
  duration: "~2 minutes"
  completed_date: "2026-06-16"
  tasks: 2
  files_modified: 1
---

# Phase 22 Plan 03: Skip 3 Invalidated zsh_parity Golden Cases (Phase Gate) Summary

**One-liner:** Surgically skipped the 3 Phase-22-invalidated parity cases (homebrew-packages, setapp-applications, web-installed-applications) via XFAIL_STEMS + pytest.skip(), keeping the full suite at 445 passed / 8 skipped / 0 failed.

## What Was Built

Phase 22's versioned output (`name (version)`) intentionally diverges from the frozen
zsh golden files, which remain name-only. To avoid both tautological golden regeneration
and false failures, exactly three parametrized parity cases are skipped at runtime.

### Changes

**`tests/test_golden_parity.py`** (27 lines inserted):

1. New module-level `XFAIL_STEMS: dict[str, str]` constant listing the three affected
   stems with reason strings that reference `ZSH-02` and `Phase 23`.
2. Three-line guard at the top of `test_section_parity`:
   ```python
   if section_stem in XFAIL_STEMS:
       pytest.skip(XFAIL_STEMS[section_stem])
   ```

No golden `.txt` files were modified. `EXPECTED_STEMS` (17 items) is unchanged.

## Verification Results

| Check | Result |
|-------|--------|
| `test_section_parity[homebrew-packages]` | SKIPPED |
| `test_section_parity[setapp-applications]` | SKIPPED |
| `test_section_parity[web-installed-applications]` | SKIPPED |
| All other 14 `test_section_parity` cases | PASSED |
| All 13 `test_live_zsh_parity` cases | PASSED |
| Full suite (`./venv/bin/python -m pytest -x -q`) | 445 passed, 8 skipped, 0 failed |
| `./venv/bin/ruff check tests/test_golden_parity.py` | 0 issues |
| `./venv/bin/mypy --strict src/maccat/` | Success: no issues in 30 files |
| `grep -c "ZSH-02" tests/test_golden_parity.py` | 5 (>= 3 required) |
| Golden `.txt` files modified | None |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 + 2 | `7bcb8b3` | fix(22-03): skip 3 invalidated zsh_parity golden cases (ZSH-02) |

## Deviations from Plan

None - plan executed exactly as written. The two tasks (edit + gate) were committed together since Task 2 produces no file changes.

## Known Stubs

None.

## Threat Flags

No new security-relevant surface introduced. This change is test-file-only; no production code, network endpoints, or auth paths modified.

## Self-Check: PASSED

- `tests/test_golden_parity.py` exists and contains `XFAIL_STEMS`
- Commit `7bcb8b3` verified in git log
- 445 passed, 8 skipped, 0 failed confirmed
