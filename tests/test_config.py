"""Tests for the Config dataclass."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_tray import Config


def test_minimal_config() -> None:
    cfg = Config(
        name="thing",
        title="Thing",
        bin="thing",
        subcommand=("serve",),
        host="localhost",
        port=8080,
        url="http://localhost:8080",
        icon_dir=Path("/tmp"),
        icon_fallback="thing-circle-64.png",
    )
    assert cfg.name == "thing"
    assert cfg.port == 8080
    assert cfg.subcommand == ("serve",)


def test_subcommand_is_normalized_to_tuple() -> None:
    cfg = Config(
        name="thing",
        title="Thing",
        bin="t",
        subcommand=["a", "b"],
        host="h",
        port=1,
        url="u",
        icon_dir=Path("/"),
        icon_fallback="f",
    )
    assert isinstance(cfg.subcommand, tuple)
    assert cfg.subcommand == ("a", "b")


def test_rejects_invalid_port_zero() -> None:
    with pytest.raises(ValueError, match="port must be 1-65535"):
        Config(
            name="t",
            title="T",
            bin="t",
            subcommand=("s",),
            host="h",
            port=0,
            url="u",
            icon_dir=Path("/"),
            icon_fallback="f",
        )


def test_rejects_invalid_port_too_high() -> None:
    with pytest.raises(ValueError, match="port must be 1-65535"):
        Config(
            name="t",
            title="T",
            bin="t",
            subcommand=("s",),
            host="h",
            port=70000,
            url="u",
            icon_dir=Path("/"),
            icon_fallback="f",
        )


def test_rejects_empty_subcommand() -> None:
    with pytest.raises(ValueError, match="subcommand must be non-empty"):
        Config(
            name="t",
            title="T",
            bin="t",
            subcommand=(),
            host="h",
            port=80,
            url="u",
            icon_dir=Path("/"),
            icon_fallback="f",
        )


def test_rejects_empty_icon_fallback() -> None:
    with pytest.raises(ValueError, match="icon_fallback must be non-empty"):
        Config(
            name="t",
            title="T",
            bin="t",
            subcommand=("s",),
            host="h",
            port=80,
            url="u",
            icon_dir=Path("/"),
            icon_fallback="",
        )


def test_rejects_invalid_name() -> None:
    with pytest.raises(ValueError, match="lowercase"):
        Config(
            name="BadName",
            title="T",
            bin="t",
            subcommand=("s",),
            host="h",
            port=80,
            url="u",
            icon_dir=Path("/"),
            icon_fallback="f",
        )


def test_env_var_host_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_THING_HOST", "10.0.0.1")
    cfg = Config(
        name="thing",
        title="T",
        bin="t",
        subcommand=("s",),
        host="localhost",
        port=8080,
        url="http://localhost:8080",
        icon_dir=Path("/"),
        icon_fallback="f",
    )
    assert cfg.host == "10.0.0.1"


def test_url_rebuilds_when_only_host_overridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HERMES_*_HOST env override must also update the URL's netloc.

    Regression: previously the URL was built from the default host
    *before* env-var overrides, so setting HERMES_*_HOST alone left
    the URL pointing at "localhost" while the liveness probe pointed
    at the real address. The Open menu opened the wrong URL.
    """
    monkeypatch.setenv("HERMES_THING_HOST", "10.0.0.1")
    cfg = Config(
        name="thing",
        title="T",
        bin="t",
        subcommand=("s",),
        host="localhost",
        port=8080,
        url="http://localhost:8080",
        icon_dir=Path("/"),
        icon_fallback="f",
    )
    assert cfg.url == "http://10.0.0.1:8080"


def test_url_rebuilds_when_only_port_overridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_THING_PORT", "9090")
    cfg = Config(
        name="thing",
        title="T",
        bin="t",
        subcommand=("s",),
        host="localhost",
        port=8080,
        url="http://localhost:8080",
        icon_dir=Path("/"),
        icon_fallback="f",
    )
    assert cfg.url == "http://localhost:9090"


def test_url_preserves_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """The router's URL ends in '/dashboard' — must survive override."""
    monkeypatch.setenv("HERMES_ROUTER_HOST", "10.0.0.1")
    cfg = Config(
        name="router",
        title="R",
        bin="r",
        subcommand=("s",),
        host="localhost",
        port=8319,
        url="http://localhost:8319/dashboard",
        icon_dir=Path("/"),
        icon_fallback="f",
    )
    assert cfg.url == "http://10.0.0.1:8319/dashboard"


def test_url_env_var_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the user sets HERMES_*_URL explicitly, use it verbatim."""
    monkeypatch.setenv("HERMES_THING_HOST", "10.0.0.1")
    monkeypatch.setenv("HERMES_THING_URL", "https://custom.example.com/x")
    cfg = Config(
        name="thing",
        title="T",
        bin="t",
        subcommand=("s",),
        host="localhost",
        port=8080,
        url="http://localhost:8080",
        icon_dir=Path("/"),
        icon_fallback="f",
    )
    assert cfg.url == "https://custom.example.com/x"


def test_url_strips_default_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """When port matches the scheme's default, the URL shouldn't show it."""
    monkeypatch.setenv("HERMES_THING_HOST", "10.0.0.1")
    monkeypatch.setenv("HERMES_THING_PORT", "80")
    cfg = Config(
        name="thing",
        title="T",
        bin="t",
        subcommand=("s",),
        host="localhost",
        port=8080,
        url="http://localhost:8080",
        icon_dir=Path("/"),
        icon_fallback="f",
    )
    assert cfg.url == "http://10.0.0.1"


def test_env_var_port_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_THING_PORT", "9090")
    cfg = Config(
        name="thing",
        title="T",
        bin="t",
        subcommand=("s",),
        host="localhost",
        port=8080,
        url="http://localhost:8080",
        icon_dir=Path("/"),
        icon_fallback="f",
    )
    assert cfg.port == 9090


def test_env_prefix_handles_hyphens() -> None:
    cfg = Config(
        name="my-thing",
        title="T",
        bin="t",
        subcommand=("s",),
        host="h",
        port=1,
        url="u",
        icon_dir=Path("/"),
        icon_fallback="f",
    )
    assert cfg.env_prefix() == "HERMES_MY_THING_"


def test_cmd_property() -> None:
    cfg = Config(
        name="thing",
        title="T",
        bin="thing",
        subcommand=("serve", "--verbose"),
        host="localhost",
        port=8080,
        url="u",
        icon_dir=Path("/"),
        icon_fallback="f",
    )
    assert cfg.cmd == ["thing", "serve", "--verbose", "--host", "localhost", "--port", "8080"]


def test_icon_fallback_path() -> None:
    cfg = Config(
        name="thing",
        title="T",
        bin="t",
        subcommand=("s",),
        host="h",
        port=1,
        url="u",
        icon_dir=Path("/tmp/icons"),
        icon_fallback="thing.png",
    )
    assert cfg.icon_fallback_path == Path("/tmp/icons/thing.png")


def test_default_log_paths() -> None:
    cfg = Config(
        name="mnemosyne",
        title="T",
        bin="t",
        subcommand=("s",),
        host="h",
        port=1,
        url="u",
        icon_dir=Path("/"),
        icon_fallback="f",
    )
    assert cfg.log_path == "~/.cache/hermes-mnemosyne.log"
    assert cfg.state_path == "~/.cache/hermes-mnemosyne.state"
    assert cfg.restart_lock_path == "~/.cache/hermes-mnemosyne.restart"


def test_frozen() -> None:
    cfg = Config(
        name="thing",
        title="T",
        bin="t",
        subcommand=("s",),
        host="h",
        port=1,
        url="u",
        icon_dir=Path("/"),
        icon_fallback="f",
    )
    with pytest.raises((AttributeError, Exception)):  # FrozenInstanceError is an AttributeError
        cfg.port = 9999  # type: ignore[misc]
