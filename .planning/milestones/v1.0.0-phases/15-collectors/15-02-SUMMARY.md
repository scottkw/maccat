---
phase: 15-collectors
plan: "02"
subsystem: collectors
tags: [homebrew, mas, subprocess, raw-write, cat-06, degradation]
dependency_graph:
  requires: [15-01-base-types]
  provides: [HomebrewCollector, MasCollector]
  affects: [15-03..15-08 (subprocess mock pattern reference), 16-orchestrator]
tech_stack:
  added: []
  patterns: [raw-write collector, subprocess mock testing, shutil.which guard]
key_files:
  created:
    - src/maccat/collectors/homebrew.py
    - src/maccat/collectors/mas.py
    - tests/collectors/test_homebrew.py
  modified: []
decisions:
  - "raw=True on all Sections for both collectors — orchestrator uses write_lines() not flush_section()"
  - "shell=False (default) + list-form subprocess calls — T-15-02-01 subprocess injection mitigation"
  - "_run() helper returns [] on non-zero exit (no exception) — graceful degradation without raising"
  - "WARNING message to sys.stderr for absent tools; fallback text goes into catalog items"
metrics:
  duration: "~10 minutes"
  completed: "2026-06-15"
  tasks_completed: 2
  files_created: 3
---

# Phase 15 Plan 02: Homebrew + mas Raw-Write Collectors Summary

Implemented HomebrewCollector (formulae + casks) and MasCollector (App Store via mas CLI) as raw-write subprocess collectors with exact byte-parity fallback messages from update-list.sh:2233-2260.

## What Was Built

**`src/maccat/collectors/homebrew.py`** — HomebrewCollector:
- `available()`: `shutil.which("brew") is not None`
- `_run(cmd)`: subprocess.run list-form, shell=False; returns [] on non-zero exit or empty stdout
- `collect()`: formulae + casks concatenated; absent-brew returns `["Homebrew is not installed."]`
- All Sections: `raw=True` — orchestrator writes via `write_lines()`, never `flush_section()`
- WARNING to sys.stderr when brew absent (not written to catalog)

**`src/maccat/collectors/mas.py`** — MasCollector:
- `available()`: `shutil.which("mas") is not None`
- `_parse_mas_output(stdout)`: Python equivalent of `awk '{print $2, $3}'` — skips column 1 (App Store ID), joins columns 2+3
- `collect()`: three paths: absent-mas (two-line fallback), non-zero exit (error message), success (parsed lines)
- All Sections: `raw=True`
- Short lines (< 3 fields) silently excluded from output

**`tests/collectors/test_homebrew.py`** — 9 tests covering both collectors:
- TestHomebrewCollector (4 tests): formulae+casks with side_effect, absent fallback, non-zero exit, title
- TestMasCollector (5 tests): parsed output, two-line absent fallback, non-zero exit, title, short-line skip
- All tests use `shutil.which` + `subprocess.run` mocking — CI-safe, no tools required

## Deviations from Plan

None — plan executed exactly as written. Minor deviation: ruff E501 on docstrings required wrapping module docstrings to < 100 chars (auto-fixed during implementation, not an architectural change).

## Success Criteria Verification

- [x] HomebrewCollector.collect() with brew available returns Section(raw=True) with brew output lines
- [x] HomebrewCollector with brew absent returns `["Homebrew is not installed."]`, raw=True
- [x] MasCollector._parse_mas_output produces "AppName (version)" lines (columns 2+3)
- [x] MasCollector with mas absent returns two-line fallback, raw=True
- [x] MasCollector with non-zero exit returns `["Could not retrieve App Store list."]`, raw=True
- [x] subprocess calls use list form, shell=False (T-15-02-01 mitigated)
- [x] ruff check clean on homebrew.py, mas.py, test_homebrew.py
- [x] mypy --strict clean on homebrew.py, mas.py (0 errors)
- [x] 9 new tests pass; full suite 203 tests pass (prior 194 + 9 new)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 7e26ecc | feat(15-02): add HomebrewCollector and MasCollector (raw-write, subprocess) |
| Task 2 | 0b6f79f | feat(15-02): add unit tests for HomebrewCollector and MasCollector |

## Known Stubs

None. Both collectors produce live subprocess data; absent-tool fallbacks match exact zsh catalog strings.

## Threat Flags

None. No new network endpoints, auth paths, or secret-bearing fields introduced.
Subprocess calls use list form (not shell string interpolation) as required by T-15-02-01.
Output fields are package names only — no secret fields reachable from brew/mas output (T-15-02-02 accepted).

## Self-Check: PASSED

Files exist:
- src/maccat/collectors/homebrew.py: FOUND
- src/maccat/collectors/mas.py: FOUND
- tests/collectors/test_homebrew.py: FOUND

Commits exist:
- 7e26ecc: FOUND
- 0b6f79f: FOUND
