---
plan: 22-01
phase: 22
title: Plist version helper + versioned Homebrew output
status: complete
requirements: [VER-01, VER-02, VER-05, VER-06]
---

# Plan 22-01 Summary — Plist Helper + Versioned Homebrew

## What was built

- **`src/maccat/helpers/plist_version.py`** (Task 1) — shared, never-raising
  `Info.plist` version reader using stdlib `plistlib`. Key precedence
  `CFBundleShortVersionString` → `CFBundleVersion` → `""`. Returns `""` on any
  failure (missing file, zero-byte, binary-unparseable, neither key present),
  mirroring the `json_io` never-raise pattern. Reused by the Setapp + WebApps
  collectors in plan 22-02. (9 unit tests in `tests/helpers/test_plist_version.py`.)
- **`src/maccat/collectors/homebrew.py`** (Task 2) — switched to
  `brew list --formula --versions` / `--cask --versions`; added
  `_parse_brew_versions_line()` which emits `name (version)` and preserves ALL
  installed versions space-joined inside the parens
  (`python@3.11 (3.11.1 3.11.2)`). Version-less lines degrade to bare name
  (VER-05). Ordering from `brew` is preserved — NOT routed through
  `flush_section` — keeping output deterministic (VER-06). `raw=True` retained.
- **`tests/collectors/test_homebrew.py`** (Task 3) — updated existing cases to the
  versioned output and added `TestHomebrewVersionParsing` (single, multi-version,
  name-only degradation, empty line, determinism).

## Requirements satisfied

- VER-01 (formulae versioned), VER-02 (casks versioned), VER-05 (graceful
  degradation), VER-06 (determinism / preserved ordering).

## Verification

- `tests/collectors/test_homebrew.py`: 15 passed.
- `tests/helpers/test_plist_version.py`: 9 passed.
- `ruff check`: clean. `mypy --strict src/maccat`: clean (30 source files).

## Deviations / notes

- **Recovered after an executor crash.** The spawned gsd-executor committed Task 1
  (`330fb5c`) and had written Task 3's `test_homebrew.py` but died (API socket
  close) before implementing Task 2 (`homebrew.py`). The orchestrator inspected the
  partial state (Task 1 committed; new tests red for lack of impl), completed the
  `homebrew.py` implementation to satisfy the already-written tests, and committed
  Task 2 + Task 3 together (`feat(22-01): versioned Homebrew ...`). No work lost or
  duplicated.
- The `mas` collector was intentionally left unchanged (already versioned).
- The full pytest suite still shows the `homebrew-packages` golden-parity case as a
  pre-existing failure-by-design; it is neutralized (skipped) in plan 22-03, not here.

## Self-Check: PASSED
