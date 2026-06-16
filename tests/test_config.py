"""Tests for maccat.config — CFG-01 through CFG-06.

All tests use disposable fixtures (tmp_path, git_repo) and monkeypatched env
vars. No test touches ~/.config/maccat or any real catalog folder.
"""
from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest

from maccat.config import (
    Config,
    _toml_string,
    config_show,
    load_config,
    resolve_archive_days,
    resolve_catalog_repo,
    validate_catalog_repo,
    write_config,
)

# ---------------------------------------------------------------------------
# TestResolveConfigPath — _default_config_path
# ---------------------------------------------------------------------------


class TestResolveConfigPath:
    def test_default_path_uses_home_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No XDG_CONFIG_HOME → path ends with .config/maccat/config.toml."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        from maccat.config import _default_config_path

        p = _default_config_path()
        assert p.parts[-3:] == (".config", "maccat", "config.toml")
        assert p.is_absolute()

    def test_xdg_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """XDG_CONFIG_HOME set → uses that base directory."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from maccat.config import _default_config_path

        p = _default_config_path()
        assert p == tmp_path / "maccat" / "config.toml"

    def test_xdg_override_path_components(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """XDG override path has maccat/config.toml appended."""
        custom = tmp_path / "custom_cfg"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(custom))
        from maccat.config import _default_config_path

        p = _default_config_path()
        assert p.name == "config.toml"
        assert p.parent.name == "maccat"
        assert p.parent.parent == custom


# ---------------------------------------------------------------------------
# TestLoadConfig
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_missing_file_returns_empty_config(self, tmp_path: Path) -> None:
        """Absent config file → Config() with catalog_dir=None."""
        missing = tmp_path / "no-such" / "config.toml"
        cfg = load_config(missing)
        assert cfg == Config()
        assert cfg.catalog_dir is None

    def test_valid_toml_populates_catalog_dir(self, tmp_path: Path) -> None:
        """config.toml with catalog_dir='/tmp/repo' → Config with that Path."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_bytes(b'catalog_dir = "/tmp/repo"\n')
        cfg = load_config(cfg_file)
        assert cfg.catalog_dir == Path("/tmp/repo")

    def test_toml_without_catalog_dir_returns_none(self, tmp_path: Path) -> None:
        """TOML file with no catalog_dir key → Config(catalog_dir=None)."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_bytes(b"# no keys\n")
        cfg = load_config(cfg_file)
        assert cfg.catalog_dir is None

    def test_malformed_toml_raises(self, tmp_path: Path) -> None:
        """Invalid TOML → tomllib.TOMLDecodeError propagates."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_bytes(b"this is not valid toml [\n")
        with pytest.raises(tomllib.TOMLDecodeError):
            load_config(cfg_file)

    def test_tilde_in_path_is_expanded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """catalog_dir with ~ is expanded via expanduser in load_config."""
        monkeypatch.setenv("HOME", str(tmp_path))
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_bytes(b'catalog_dir = "~/myrepo"\n')
        cfg = load_config(cfg_file)
        # expanduser resolves ~ → HOME value
        assert cfg.catalog_dir == Path(str(tmp_path) + "/myrepo")


# ---------------------------------------------------------------------------
# TestResolveCatalogRepo  (CFG-01 precedence chain)
# ---------------------------------------------------------------------------


class TestResolveCatalogRepo:
    def test_flag_wins_over_env_and_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All three sources set: --catalog-dir flag wins."""
        flag_dir = tmp_path / "flag_dir"
        flag_dir.mkdir()
        env_dir = tmp_path / "env_dir"
        env_dir.mkdir()
        cfg_dir = tmp_path / "cfg_dir"
        cfg_dir.mkdir()

        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(env_dir))
        cfg = Config(catalog_dir=cfg_dir)

        result = resolve_catalog_repo(str(flag_dir), cfg)
        assert result == flag_dir.resolve()

    def test_env_wins_over_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No flag, env set, config set: MACCAT_CATALOG_DIR env wins."""
        env_dir = tmp_path / "env_dir"
        env_dir.mkdir()
        cfg_dir = tmp_path / "cfg_dir"
        cfg_dir.mkdir()

        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(env_dir))
        monkeypatch.delenv("MACCAT_CATALOG_DIR", raising=False)  # ensure clean state
        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(env_dir))
        cfg = Config(catalog_dir=cfg_dir)

        result = resolve_catalog_repo(None, cfg)
        assert result == env_dir.resolve()

    def test_config_used_when_no_flag_or_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No flag, no env: config.catalog_dir is used."""
        cfg_dir = tmp_path / "cfg_dir"
        cfg_dir.mkdir()

        monkeypatch.delenv("MACCAT_CATALOG_DIR", raising=False)
        cfg = Config(catalog_dir=cfg_dir)

        result = resolve_catalog_repo(None, cfg)
        assert result == cfg_dir.resolve()

    def test_all_absent_raises_systemexit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nothing set → SystemExit with actionable message listing all three options."""
        monkeypatch.delenv("MACCAT_CATALOG_DIR", raising=False)
        cfg = Config()
        with pytest.raises(SystemExit) as exc_info:
            resolve_catalog_repo(None, cfg)
        msg = str(exc_info.value)
        assert "--catalog-dir" in msg
        assert "MACCAT_CATALOG_DIR" in msg
        assert "maccat config init" in msg

    def test_flag_not_written_back(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CFG-03: resolve_catalog_repo with flag_val does NOT call write_config."""
        flag_dir = tmp_path / "flag_dir"
        flag_dir.mkdir()
        monkeypatch.delenv("MACCAT_CATALOG_DIR", raising=False)
        cfg = Config()

        # Patch write_config to detect any call
        with patch("maccat.config.write_config") as mock_write:
            resolve_catalog_repo(str(flag_dir), cfg)
        mock_write.assert_not_called()

    def test_env_var_name_is_maccat_catalog_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The env var name is exactly MACCAT_CATALOG_DIR (not MAC_CATALOG_DIR)."""
        env_dir = tmp_path / "env_dir"
        env_dir.mkdir()

        # Wrong name should NOT be picked up
        monkeypatch.delenv("MACCAT_CATALOG_DIR", raising=False)
        monkeypatch.setenv("MAC_CATALOG_DIR", str(env_dir))  # stale name from research
        cfg = Config()
        with pytest.raises(SystemExit):
            resolve_catalog_repo(None, cfg)

    def test_flag_path_resolved_to_absolute(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Flag path is expanded and resolved to an absolute path."""
        flag_dir = tmp_path / "flag"
        flag_dir.mkdir()
        monkeypatch.delenv("MACCAT_CATALOG_DIR", raising=False)
        result = resolve_catalog_repo(str(flag_dir), Config())
        assert result.is_absolute()


# ---------------------------------------------------------------------------
# TestValidateCatalogRepo  (CFG-06)
# ---------------------------------------------------------------------------


class TestValidateCatalogRepo:
    def test_missing_dir_raises(self, tmp_path: Path) -> None:
        """validate_catalog_repo on a nonexistent directory → SystemExit."""
        missing = tmp_path / "nonexistent"
        with pytest.raises(SystemExit) as exc_info:
            validate_catalog_repo(missing)
        assert "not found" in str(exc_info.value)
        assert "maccat config init" in str(exc_info.value)

    def test_non_git_dir_raises(self, tmp_path: Path) -> None:
        """validate_catalog_repo on a plain directory (no .git) → SystemExit."""
        plain = tmp_path / "plain_dir"
        plain.mkdir()
        with pytest.raises(SystemExit) as exc_info:
            validate_catalog_repo(plain)
        assert "not a git repository" in str(exc_info.value)
        assert "maccat config init" in str(exc_info.value)

    def test_valid_git_no_remote_warns(
        self, git_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """git_repo fixture (no remote) → prints warning, no exception raised."""
        # Should not raise
        validate_catalog_repo(git_repo)
        out = capsys.readouterr().out
        assert "WARNING" in out
        assert "No git remote" in out

    def test_valid_git_with_remote_silent(
        self, git_repo: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        """Git repo with a remote configured → no exception, no warning."""
        # Add a fake local remote
        remote_path = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote_path)], capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", str(remote_path)],
            cwd=git_repo,
            capture_output=True,
        )
        validate_catalog_repo(git_repo)
        out = capsys.readouterr().out
        assert "WARNING" not in out

    def test_subdir_of_parent_repo_rejected(self, git_repo: Path) -> None:
        """WR-06: a plain subdirectory that merely lives INSIDE a git working tree
        (a parent repo) must NOT pass validation — commits would otherwise land in
        the wrong repository. Only the repo top-level is a valid catalog dir.
        """
        from maccat.config import _is_git_repo

        subdir = git_repo / "notes" / "catalog"
        subdir.mkdir(parents=True)
        # The subdir is inside git_repo's working tree but is NOT the toplevel.
        assert _is_git_repo(subdir) is False, (
            "a subdir under a parent git repo must not be treated as a git repo root"
        )
        with pytest.raises(SystemExit) as exc_info:
            validate_catalog_repo(subdir)
        assert "not a git repository" in str(exc_info.value)

    def test_repo_toplevel_accepted(self, git_repo: Path) -> None:
        """WR-06: the repo top-level itself IS a valid git repo (positive case)."""
        from maccat.config import _is_git_repo

        assert _is_git_repo(git_repo) is True


# ---------------------------------------------------------------------------
# TestTomlStringEscaping  (_toml_string)
# ---------------------------------------------------------------------------


class TestTomlStringEscaping:
    def test_simple_path_no_escaping(self) -> None:
        """Normal Unix path: no escaping needed."""
        assert _toml_string("/Users/ken/catalog") == '"/Users/ken/catalog"'

    def test_backslash_escaped(self) -> None:
        """Backslash in path → doubled backslash in TOML string."""
        result = _toml_string("C:\\Users\\repo")
        assert "\\\\" in result
        assert result == '"C:\\\\Users\\\\repo"'

    def test_double_quote_escaped(self) -> None:
        """Double-quote in string → escaped with backslash."""
        result = _toml_string('path/with"quote')
        assert '\\"' in result

    def test_backslash_before_quote_both_escaped(self) -> None:
        """Backslash immediately before quote: both must be escaped (order matters)."""
        result = _toml_string('path\\"end')
        # \\ → \\\\ first, then " → \"
        assert result == '"path\\\\\\"end"'

    def test_toml_parses_escaped_backslash(self, tmp_path: Path) -> None:
        """Round-trip: _toml_string output is valid TOML that tomllib can parse."""
        path_str = "C:\\Users\\ken\\catalog"
        toml_content = f"catalog_dir = {_toml_string(path_str)}\n"
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text(toml_content, encoding="utf-8")
        with open(cfg_file, "rb") as f:
            parsed = tomllib.load(f)
        assert parsed["catalog_dir"] == path_str


# ---------------------------------------------------------------------------
# TestWriteConfig  (atomic write + round-trip)
# ---------------------------------------------------------------------------


class TestWriteConfig:
    def test_write_config_creates_file(self, tmp_path: Path) -> None:
        """write_config produces a config.toml file."""
        cfg_path = tmp_path / "maccat" / "config.toml"
        write_config(cfg_path, Path("/my/catalog"))
        assert cfg_path.exists()

    def test_write_config_atomic_no_tmp_remains(self, tmp_path: Path) -> None:
        """After write_config, no .tmp file remains in the config directory."""
        cfg_path = tmp_path / "maccat" / "config.toml"
        write_config(cfg_path, Path("/my/catalog"))
        tmp_files = list((tmp_path / "maccat").glob("*.tmp"))
        assert tmp_files == [], f"Unexpected .tmp files: {tmp_files}"

    def test_write_config_creates_parent_dirs(self, tmp_path: Path) -> None:
        """write_config creates parent directories if they don't exist."""
        cfg_path = tmp_path / "deep" / "nested" / "config.toml"
        write_config(cfg_path, Path("/my/catalog"))
        assert cfg_path.exists()

    def test_load_reads_what_write_config_wrote(self, tmp_path: Path) -> None:
        """Round-trip: write_config then load_config → identical catalog_dir."""
        catalog = Path("/some/catalog/repo")
        cfg_path = tmp_path / "config.toml"
        write_config(cfg_path, catalog)
        cfg = load_config(cfg_path)
        assert cfg.catalog_dir == catalog

    def test_write_config_content_is_flat_key(self, tmp_path: Path) -> None:
        """Written TOML uses flat catalog_dir key (not a [catalog] table)."""
        cfg_path = tmp_path / "config.toml"
        write_config(cfg_path, Path("/my/catalog"))
        content = cfg_path.read_text(encoding="utf-8")
        assert content.startswith("catalog_dir = ")
        assert "[catalog]" not in content


# ---------------------------------------------------------------------------
# TestConfigShow
# ---------------------------------------------------------------------------


class TestConfigShow:
    def test_flag_source_shown(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """config_show with flag_val prints [from: --catalog-dir flag]."""
        monkeypatch.delenv("MACCAT_CATALOG_DIR", raising=False)
        flag_dir = tmp_path / "flag"
        flag_dir.mkdir()
        config_show(str(flag_dir), Config(), config_path=tmp_path / "config.toml")
        out = capsys.readouterr().out
        assert "[from: --catalog-dir flag]" in out
        assert "Config file:" in out

    def test_env_source_shown(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """config_show with MACCAT_CATALOG_DIR env prints [from: MACCAT_CATALOG_DIR env var]."""
        env_dir = tmp_path / "env"
        env_dir.mkdir()
        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(env_dir))
        config_show(None, Config(), config_path=tmp_path / "config.toml")
        out = capsys.readouterr().out
        assert "[from: MACCAT_CATALOG_DIR env var]" in out

    def test_config_file_source_shown(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """config_show with config.catalog_dir prints [from: config file]."""
        monkeypatch.delenv("MACCAT_CATALOG_DIR", raising=False)
        cfg_dir = tmp_path / "cfg"
        cfg_dir.mkdir()
        cfg = Config(catalog_dir=cfg_dir)
        config_show(None, cfg, config_path=tmp_path / "config.toml")
        out = capsys.readouterr().out
        assert "[from: config file]" in out

    def test_not_configured_shown(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """config_show with nothing set prints (not configured) and config init hint."""
        monkeypatch.delenv("MACCAT_CATALOG_DIR", raising=False)
        config_show(None, Config(), config_path=tmp_path / "config.toml")
        out = capsys.readouterr().out
        assert "(not configured)" in out
        assert "maccat config init" in out

    def test_config_file_path_always_printed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Config file path is always printed regardless of source."""
        monkeypatch.delenv("MACCAT_CATALOG_DIR", raising=False)
        cfg_path = tmp_path / "config.toml"
        config_show(None, Config(), config_path=cfg_path)
        out = capsys.readouterr().out
        assert str(cfg_path) in out

    def test_flag_wins_over_env_in_show(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When flag and env both set, show reports [from: --catalog-dir flag]."""
        flag_dir = tmp_path / "flag"
        flag_dir.mkdir()
        env_dir = tmp_path / "env"
        env_dir.mkdir()
        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(env_dir))
        config_show(str(flag_dir), Config(), config_path=tmp_path / "config.toml")
        out = capsys.readouterr().out
        assert "[from: --catalog-dir flag]" in out
        assert "MACCAT_CATALOG_DIR" not in out


# ---------------------------------------------------------------------------
# TestResolveArchiveDays
# ---------------------------------------------------------------------------


class TestResolveArchiveDays:
    def test_flag_val_used_when_provided(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """flag_val provided → returned directly and announced."""
        result = resolve_archive_days(14)
        assert result == 14
        out = capsys.readouterr().out
        assert "14 days" in out

    def test_flag_val_zero_raises(self) -> None:
        """WR-01 (iter 2): --archive-days 0 → SystemExit (must be >= 1).

        Mirrors the interactive path and the zsh contract, which rejects any
        value < 1 at parse time (update-list.sh:230-233). Without this guard a
        zero/negative period would push the prune cutoff such that archives
        that should be retained get deleted (retention.py:34).
        """
        with pytest.raises(SystemExit) as exc_info:
            resolve_archive_days(0)
        assert "at least 1 day" in str(exc_info.value)

    def test_flag_val_negative_raises(self) -> None:
        """WR-01 (iter 2): --archive-days -5 → SystemExit (data-loss guard).

        A negative retention period moves the prune cutoff into the future,
        which would over-delete archives. The flag path must reject it before
        the value ever reaches prune_old_archives.
        """
        with pytest.raises(SystemExit) as exc_info:
            resolve_archive_days(-5)
        assert "got -5" in str(exc_info.value)

    def test_flag_val_one_accepted(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """WR-01 (iter 2): the boundary value 1 (smallest valid) is accepted."""
        result = resolve_archive_days(1)
        assert result == 1
        assert "1 days" in capsys.readouterr().out

    def test_non_tty_returns_default(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Non-TTY stdin with no flag → default returned with non-interactive note."""
        with patch("maccat.config.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = False
            result = resolve_archive_days(None, default=30)
        assert result == 30
        out = capsys.readouterr().out
        assert "non-interactive" in out

    def test_interactive_empty_returns_default(self) -> None:
        """Interactive: empty input → default returned."""
        with patch("maccat.config.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = True
            with patch("builtins.input", return_value=""):
                result = resolve_archive_days(None, default=45)
        assert result == 45

    def test_interactive_valid_int_returned(self) -> None:
        """Interactive: valid positive integer entered → returned."""
        with patch("maccat.config.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = True
            with patch("builtins.input", return_value="90"):
                result = resolve_archive_days(None, default=30)
        assert result == 90

    def test_interactive_invalid_int_raises(self) -> None:
        """Interactive: non-integer input → SystemExit."""
        with patch("maccat.config.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = True
            with patch("builtins.input", return_value="abc"):
                with pytest.raises(SystemExit):
                    resolve_archive_days(None, default=30)

    def test_interactive_zero_raises(self) -> None:
        """Interactive: 0 days → SystemExit (must be >= 1)."""
        with patch("maccat.config.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = True
            with patch("builtins.input", return_value="0"):
                with pytest.raises(SystemExit):
                    resolve_archive_days(None, default=30)

    def test_interactive_eof_returns_default(self) -> None:
        """WR-04: Interactive EOF (Ctrl-D) → keep the default (zsh parity).

        The zsh `resolve_archive_retention` uses `read -r input`, which on EOF
        leaves `input` empty and falls through to "empty → keep default"
        (update-list.sh:527-531). EOF must NOT abort the run.
        """
        with patch("maccat.config.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = True
            with patch("builtins.input", side_effect=EOFError):
                result = resolve_archive_days(None, default=30)
        assert result == 30

    def test_interactive_eof_returns_default_custom(self) -> None:
        """WR-04: EOF returns the supplied default, not a hardcoded 30."""
        with patch("maccat.config.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = True
            with patch("builtins.input", side_effect=EOFError):
                result = resolve_archive_days(None, default=45)
        assert result == 45

    def test_interactive_eof_prints_terminating_newline(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """WR-04: EOF still emits the prompt-terminating newline before
        returning the default (presentation parity)."""
        with patch("maccat.config.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = True
            with patch("builtins.input", side_effect=EOFError):
                result = resolve_archive_days(None, default=30)
        assert result == 30
        assert capsys.readouterr().out.endswith("\n")
