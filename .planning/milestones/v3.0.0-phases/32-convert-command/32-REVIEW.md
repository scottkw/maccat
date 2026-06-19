---
phase: 32-convert-command
reviewed: 2026-06-18T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/maccat/convert.py
  - src/maccat/gitops.py
  - src/maccat/cli.py
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 32: Code Review Report

**Reviewed:** 2026-06-18
**Depth:** standard (new convert code paths only)
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the Phase 32 `maccat convert` implementation: `convert.py` (full file), `gitops.git_commit_convert`, and the `convert` subparser/dispatch in `cli.py`. The locked design decisions (timestamp mismatch by design, no-clobber guard, frontmatter synthesis, repo heuristic) were verified and not re-litigated.

The implementation is broadly correct. The atomicity invariant (write .md before deleting .txt) holds for the common case: a `write_text` failure leaves the .txt untouched. Three warnings were found covering: (1) an uncaught `UnicodeDecodeError` that contradicts the "never raises" comment; (2) an unhandled `OSError` from `txt_path.unlink()` that strands the user with no actionable guidance; and (3) a missing `--rename` guard that causes silent ignore of an incompatible flag. One info item covers misleading inline documentation.

No critical/security issues were found. Shell injection is not possible (`shell=False` throughout `gitops.py`). The regex is anchored and correct. No credentials or execution of parsed content.

## Warnings

### WR-01: `parse_catalog` raises `UnicodeDecodeError` for non-UTF-8 .txt files — contradicts "never raises" comment

**File:** `src/maccat/convert.py:84-85`

**Issue:** The inline comment at line 84 reads `"# 5. Parse the legacy .txt (never raises -- CONV-03: graceful degradation)"`. This is incorrect. `parse_catalog` calls `Path.read_text(encoding='utf-8')`, which raises `UnicodeDecodeError` if the file contains bytes that are not valid UTF-8. That exception is not caught anywhere in `run_convert` or its callers. The result is an unhandled Python traceback and a non-zero exit, rather than the `sys.exit("ERROR: ...")` pattern used everywhere else in `run_convert`. A user who passes a catalog with even a single non-UTF-8 byte (e.g., a legacy catalog from an older Zsh iteration that used the system locale) will see a raw traceback instead of a clean error message.

**Fix:** Wrap the `parse_catalog` call in a `try/except UnicodeDecodeError` and exit cleanly:

```python
try:
    parsed = parse_catalog(txt_path)
except UnicodeDecodeError as exc:
    sys.exit(
        f"ERROR: Catalog file is not valid UTF-8 and cannot be read: {txt_path}\n"
        f"  {exc}"
    )
```

Also correct the comment: `parse_catalog` does _not_ never-raise; it is only graceful for structural parsing issues.

---

### WR-02: `txt_path.unlink()` failure strands user with complete .md and no actionable guidance

**File:** `src/maccat/convert.py:118-121`

**Issue:** Lines 118 and 121 have no exception handling:

```python
md_path.write_text(content, encoding="utf-8")   # line 118
txt_path.unlink()                                 # line 121
```

If `write_text` raises, `unlink` is correctly not called (the .txt is safe). However if `write_text` **succeeds** and `unlink` subsequently raises (e.g., `PermissionError` on a read-only filesystem, or the file was deleted by a concurrent process), the exception propagates as an unhandled Python traceback. At that point the .md is fully written and correct, but `git_commit_convert` is never called — the .md exists on disk but is not committed. On a re-run, the no-clobber guard at line 78 blocks with `"ERROR: Target already exists"`, which does not mention that the .md may already be the correct conversion artifact. The user has no guidance from the tool on what the .md is or whether it is valid.

**Fix:** Catch `OSError` on the `unlink` call and print a targeted, actionable message:

```python
md_path.write_text(content, encoding="utf-8")
try:
    txt_path.unlink()
except OSError as exc:
    # .md is complete; .txt could not be removed.
    # Print diagnostic and let the user decide — do NOT call sys.exit here
    # because the .md is a valid artifact that should not be lost.
    print(
        f"  WARNING: Converted .md was written but .txt could not be removed: {exc}\n"
        f"  The converted file is at: {md_path}\n"
        f"  Remove {txt_path} manually, then run: maccat convert --from {txt_path} "
        f"--no-commit  (or commit the .md manually with git)"
    )
    return
```

Stopping with `return` (rather than `sys.exit`) after the warning keeps the `print("Converted: ...")` message from appearing (since `return` is before it), but the warning message itself contains the relevant file paths. An alternative is to call git commit on the .md alone before returning, but that requires a more invasive change.

---

### WR-03: `--rename` flag is silently ignored when `convert` subcommand is used

**File:** `src/maccat/cli.py:286-289`

**Issue:** The `reinstall` subcommand dispatch (lines 276-278 and 304-306) explicitly rejects the `--rename` flag with `sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")`. The `convert` dispatch at lines 286-289 does not perform this check:

```python
if args.subcommand == "convert":
    from maccat.convert import run_convert
    run_convert(args)
    return
```

As a result, `maccat --rename convert --from foo.txt` silently ignores `--rename` and performs the conversion. The rename workflow never executes. A user who accidentally combines these flags gets no error and the wrong behavior (convert runs instead of rename). The inconsistency is a silent correctness trap.

**Fix:** Add the same guard used by `reinstall`, immediately before the `run_convert` call:

```python
if args.subcommand == "convert":
    if args.rename:
        sys.exit("ERROR: --rename cannot be combined with the 'convert' subcommand.")
    from maccat.convert import run_convert
    run_convert(args)
    return
```

## Info

### IN-01: "never raises" comment is misleading regardless of the UnicodeDecodeError fix

**File:** `src/maccat/convert.py:84`

**Issue:** Even after fixing WR-01, the comment `"# 5. Parse the legacy .txt (never raises -- CONV-03: graceful degradation)"` conflates two separate claims: (a) `parse_catalog` never raises for _structural_ parsing failures (true — it degrades gracefully for malformed section formatting), and (b) `parse_catalog` never raises at all (false — I/O and encoding errors always escape). The comment should be narrowed to its accurate scope.

**Fix:** Replace the comment with:

```python
# 5. Parse the legacy .txt.
# parse_catalog degrades gracefully for structural anomalies (missing separators,
# empty sections, unknown lines) — it never raises for catalog content issues.
# I/O errors (UnicodeDecodeError, PermissionError) are caught above.
```

---

_Reviewed: 2026-06-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard (new convert code paths only)_
