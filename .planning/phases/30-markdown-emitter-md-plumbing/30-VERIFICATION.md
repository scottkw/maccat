---
phase: 30-markdown-emitter-md-plumbing
verified: 2026-06-18T19:54:36Z
status: passed
score: 5/5
overrides_applied: 0
---

# Phase 30: Markdown Emitter & `.md` Plumbing — Verification Report

**Phase Goal:** Catalog generation produces a rendered markdown `.md` snapshot — YAML frontmatter provenance, a `#` title, and one `##` per-source section rendering items as a uniform `Name | Version | ID` table — and every `.txt`-keyed file behavior (filename pattern, newest-per-computer retention, archive pruning, git staging) moves to `.md`.

**Verified:** 2026-06-18T19:54:36Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A catalog run writes `mac-software-list-[computer]-YYYYMMDDHHMMSS.md`; file opens with YAML frontmatter (computer, hostname, generated, maccat_version) followed by a `#` title | VERIFIED | `naming.py:71` returns `.md` extension; `render_markdown_catalog` opens with `render_frontmatter` block then `# Installed Mac Software List\n`; behavioral spot-check confirmed exact byte output |
| 2 | Every one of the 22 sources renders as a `##` heading with a three-column `Name \| Version \| ID` table; missing version/ID renders empty cell; no-items source renders `(none found)` | VERIFIED | `markdown.py:177` appends `\n## {section.title}\n`; `_render_table` builds `\| Name \| Version \| ID \|` header + `\| --- \| --- \| --- \|`; empty/degraded path appends `(none found)\n`; spot-check confirmed both table and `(none found)` output |
| 3 | Two consecutive runs produce byte-identical `.md` output; secret-scan finds zero MCP credentials (FMT-01/FMT-03/FMT-04) | VERIFIED | `render_markdown_catalog` is a pure function; frontmatter keys are in fixed order; non-raw sections use `flush_section` (LC_ALL=C sort -f -u); determinism spot-check passed (r == r2 with fixed timestamp); `TestDeterminism` class in test suite passes; FMT-03 preserved upstream — emitter re-parses already-clean item strings |
| 4 | Newest-per-computer retention and age-based archive pruning operate on `.md` catalogs only; stray `.txt` is left untouched | VERIFIED | `retention.py:64,75,118` all glob `mac-software-list-*.md`; `identity.py:158,549` both glob `mac-software-list-*.md`; no `.txt` glob remains in production source; `test_safety_invariants.py:60` uses `.md` malformed filename for invariant test; `parse_catalog_filename` returns `None` for `.txt` filenames |
| 5 | git pull → generate → commit/push cycle stages `.md` additions, archive moves, and deletions in one commit; `--no-commit` performs all file operations while skipping git | VERIFIED | `gitops.py:119` uses `git add -A -- {computer}/` (extension-agnostic); `cli.py:349` gates `git_commit_and_push` on `auto_commit`; `CatalogWriter.write_raw` is always called regardless of `--no-commit`; `test_cli.py` five glob assertions all use `*.md` — all pass |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/maccat/catalog/markdown.py` | `render_markdown_catalog`, `render_frontmatter`, `_render_table`, `_parse_columns`, `_escape_cell` | VERIFIED | File exists; all 5 functions present; pure — no I/O; ruff + mypy --strict clean |
| `src/maccat/catalog/writer.py` | `CatalogWriter.write_raw` method | VERIFIED | `write_raw` at line 80; assert guard present; writes content atomically via tmp+rename |
| `tests/test_markdown_emitter.py` | 7 test classes covering all behaviors | VERIFIED | 8 classes found: `TestFrontmatter`, `TestTableRendering`, `TestPipeEscaping`, `TestEmptySections`, `TestDegradedSections`, `TestRawVsNonRaw`, `TestDeterminism`, `TestWriteRaw` |
| `src/maccat/naming.py` | `.md` extension in `_FILENAME_RE` and `make_catalog_filename` | VERIFIED | `_FILENAME_RE` at line 19 matches `\.md$`; `make_catalog_filename` returns `...{timestamp}.md` |
| `src/maccat/retention.py` | Three glob sites use `mac-software-list-*.md` | VERIFIED | Lines 64, 75, 118 all use `.md` glob |
| `src/maccat/identity.py` | Two glob sites use `mac-software-list-*.md` | VERIFIED | Lines 158, 549 both use `.md` glob |
| `src/maccat/cli.py` | Generate loop uses `render_markdown_catalog` + `write_raw`; `socket.gethostname()`; `generated_iso` | VERIFIED | Lines 173-334: `import socket`, `render_markdown_catalog`, `Section`, `all_sections`, `generated_iso`, `write_raw` all present; old `write_section("Installed Mac Software List")` call removed |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli.py` | `catalog/markdown.render_markdown_catalog` | deferred import inside `run()` | WIRED | `from maccat.catalog.markdown import render_markdown_catalog` at line 176; called at line 321 with all 5 kwargs |
| `cli.py` | `catalog/writer.CatalogWriter.write_raw` | `w.write_raw(content)` | WIRED | `write_raw(content)` at line 334 inside `CatalogWriter` context manager |
| `cli.py` | `naming.make_catalog_filename` | `filename = make_catalog_filename(computer, timestamp)` | WIRED | Line 329; returns `.md` filename |
| `catalog/markdown.py` | `catalog/format.flush_section` | `from maccat.catalog.format import flush_section` + call | WIRED | Import at line 27; called at line 189 for non-raw path |
| `retention.py` | `naming.parse_catalog_filename` | `cf = parse_catalog_filename(f.name)` | WIRED | Called in both passes of `retain_newest_per_host` and in `prune_old_archives` |
| `identity.py` | `naming.make_catalog_filename` | called in rename loop | WIRED | Line 549 glob + `make_catalog_filename` used to build renamed path |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `cli.py` generate loop | `all_sections` | `get_registry()` collectors | Yes — each collector runs live detection and returns `Section` objects | FLOWING |
| `cli.py` | `content` | `render_markdown_catalog(all_sections, ...)` | Yes — pure transform of real collector output | FLOWING |
| `cli.py` | written file | `CatalogWriter.write_raw(content)` | Yes — atomic tmp+rename ensures complete file or no file | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `render_markdown_catalog` produces YAML frontmatter with double-quoted `generated` | `python -c "from maccat.catalog.markdown import render_markdown_catalog..."` | frontmatter keys in correct order; `generated: "2026-06-18T12:34:56"` present | PASS |
| Each section renders as `## heading` + 3-col table | Same spot-check | `## Homebrew Packages\n\| Name \| Version \| ID \|...` confirmed | PASS |
| Empty section renders `(none found)` | Same spot-check | `(none found)` present under `## App Store Applications` | PASS |
| Pipe in item value is escaped `\|` | Separate check with `foo \| bar` item | `\|` present in rendered output | PASS |
| `make_catalog_filename` returns `.md` | `python -c "from maccat.naming import make_catalog_filename..."` | `mac-software-list-[TestMac]-20260618123456.md` | PASS |
| `.txt` filename returns `None` from `parse_catalog_filename` | Same | `None` returned | PASS |
| `write_raw` writes content atomically | File read after `CatalogWriter` context | content byte-exact | PASS |
| Determinism: two calls same args → identical output | `r == r2` assertion | Equal | PASS |
| Full test suite green | `./venv/bin/pytest tests/ -x -q` | `672 passed in 16.55s` | PASS |
| ruff check all modified files | `./venv/bin/ruff check ...` | `All checks passed!` | PASS |
| mypy --strict all modified files | `./venv/bin/mypy --strict ...` | `Success: no issues found in 6 source files` | PASS |

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| MD-01 | Catalog writes `.md`; filename pattern `mac-software-list-[computer]-YYYYMMDDHHMMSS.md` | SATISFIED | `naming.py:19,71`; `cli.py:329`; test_naming.py and test_cli.py all pass |
| MD-02 | YAML frontmatter block: computer, hostname, generated (double-quoted), maccat_version + `#` title | SATISFIED | `markdown.py:112-133` render_frontmatter; `markdown.py:173`; spot-check confirmed |
| MD-03 | Every source renders `##` heading + `Name \| Version \| ID` table; missing cells render empty | SATISFIED | `markdown.py:177,91-109`; `TestTableRendering` passes |
| MD-04 | No-items source renders `(none found)` under heading | SATISFIED | `markdown.py:184,192`; `TestEmptySections` and `TestDegradedSections` pass |
| MD-05 | Deterministic, stably sorted; no secrets in output | SATISFIED | Fixed key order in frontmatter; `flush_section` for non-raw; `TestDeterminism` passes; MCP secret invariant upheld upstream (collectors never include credentials in item strings) |
| FILE-01 | Retention/archive pruning on `.md` only; `.txt` glob replaced not duplicated | SATISFIED | `retention.py:64,75,118` and `identity.py:158,549` all `.md`; no `.txt` glob in production source |
| FILE-02 | git cycle stages `.md` additions, archive moves, deletions; `--no-commit` skips git | SATISFIED | `gitops.py:119` uses `git add -A -- {computer}/` (extension-agnostic); `cli.py:349` `auto_commit` gate; `test_cli.py` five `*.md` assertions all pass |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | Scan of all 7 modified files: no TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers; no stub returns (null/\[\]/\{\}); no hardcoded empty data flowing to rendering |

---

### Human Verification Required

None. All success criteria are verifiable programmatically. The format is deterministic and the test suite covers all 7 phase requirements. No browser, visual, real-time, or external-service behavior is involved.

---

### Gaps Summary

No gaps. All 5 roadmap success criteria verified. All 7 requirements (MD-01 through MD-05, FILE-01, FILE-02) satisfied. Full test suite (672 tests) passes. ruff and mypy --strict clean on all modified files.

---

_Verified: 2026-06-18T19:54:36Z_
_Verifier: Claude (gsd-verifier)_
