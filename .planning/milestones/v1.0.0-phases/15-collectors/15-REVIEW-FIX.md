---
phase: 15-collectors
fixed_at: 2026-06-14T00:00:00Z
review_path: .planning/phases/15-collectors/15-REVIEW.md
iteration: 2
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 15: Code Review Fix Report

**Fixed at:** 2026-06-14
**Source review:** .planning/phases/15-collectors/15-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope (Critical + Warning): 2
- Fixed (accepted + documented): 2
- Skipped: 0

Both iteration-2 warnings (WR-01, WR-02) describe narrow divergences from the zsh
reference that occur only on degenerate/misshaped input. They were reviewed and
**accepted as intentional, better-than-zsh degradations** rather than changed to
reproduce zsh's data-losing (jq stream-abort) / garbage-emitting (awk space-only
line) behavior. The resolution is documentation-only: a concise
`# PARITY DEVIATION (intentional)` comment was added at each affected site so a
future reader does not mistake the divergence for a parity bug. No runtime behavior
changed — neither divergence affects Phase 17 golden parity on real data.

Verification after the comment-only edits:
- `PYTHONPATH=src ./venv/bin/pytest -q` → 351 passed (unchanged from iteration 1,
  proving the edits are doc-only with zero behavior change)
- `./venv/bin/ruff check src/maccat tests` → All checks passed
- `./venv/bin/mypy --strict src/maccat` → only the known acceptable Phase-16
  `maccat.cli` stub import error at `__main__.py:20`

## Fixed Issues

### WR-01: MCP/Firefox per-entry shape guard `continue` vs jq stream-abort (accepted, documented)

**Files modified:** `src/maccat/collectors/claude.py`, `src/maccat/collectors/opencode.py`, `src/maccat/collectors/gemini.py`, `src/maccat/collectors/firefox.py`
**Commit:** 6b64d4c
**Applied fix:** No behavioral change. Added a `# PARITY DEVIATION (intentional, WR-01)`
comment at each per-entry shape-guard site (the `isinstance(cfg, dict)` skip in the
three MCP loops and the `isinstance(addon, dict)` skip in the Firefox addon loop),
explaining that the per-entry skip is intentionally more robust than zsh's single
`jq` invocation (which aborts the entire section on the first non-object value), and
that it only diverges on malformed configs absent from real data — so golden parity
is unaffected. The accept-as-intentional decision was directed by the orchestrator;
the byte-divergence only manifests on misshaped input that real tool configs never
produce.

### WR-02: mas `_parse_mas_output` drops blank/1-field lines vs awk space-only line (accepted, documented)

**Files modified:** `src/maccat/collectors/mas.py`
**Commit:** 6b64d4c
**Applied fix:** No behavioral change. Added a `# PARITY DEVIATION (intentional, WR-02)`
comment at the line-drop site in `_parse_mas_output`, explaining that a 0/1-field or
blank line makes `awk '{print $2, $3}'` emit a lone space-only line whereas the Python
port drops it, that real `mas list` always emits >=3 fields, and that the divergence
therefore only occurs on degenerate input and does not affect golden parity on real
data.

## Notes

- **Documentation-only iteration.** No runtime code paths were altered; the only
  source changes are inline comments. The unchanged 351-passed test count is the
  evidence that behavior is identical to iteration 1.
- **No new files created and no fixes skipped.** Both in-scope warnings were
  resolved by documenting the accepted deviation.
- **CAT-05 invariant untouched:** the comments sit at existing shape-guard sites and
  introduce no new field reads.

---

_Fixed: 2026-06-14_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
