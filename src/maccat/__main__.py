"""maccat entry point — version guard fires before any package imports."""
# VERSION GUARD — must be first executable code; no package imports before this check
import sys

if sys.version_info < (3, 11):  # noqa: UP036  intentional fail-fast guard (PKG-02): the guard exists precisely to catch interpreters older than the 3.11 floor; do not remove.
    sys.exit(
        f"maccat requires Python 3.11 or later.\n"
        f"You are running Python {sys.version_info.major}.{sys.version_info.minor}.\n"
        f"\n"
        f"Install a supported version:\n"
        f"  Homebrew: brew install python@3.11\n"
        f"  Direct:   https://python.org/downloads/\n"
        f"\n"
        f"Note: /usr/bin/python3 on macOS is Python 3.9 (EOL). Use Homebrew Python."
    )


# Only import from the package AFTER the version check
def main() -> None:
    from maccat.cli import run
    run()


if __name__ == "__main__":
    main()
