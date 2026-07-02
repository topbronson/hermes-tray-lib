"""Tests for the Indicator class."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from hermes_tray import Config, Indicator, State


def _make_config(icon_dir: Path) -> Config:
    return Config(
        name="thing",
        title="Thing",
        bin="t",
        subcommand=("s",),
        host="h",
        port=1,
        url="u",
        icon_dir=icon_dir,
        icon_fallback="thing-circle-64.png",
    )


def test_starts_in_stopped_state(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    ind = Indicator(cfg, indicator_ref=MagicMock())
    assert ind.current is State.STOPPED


def test_set_state_persists(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    ind = Indicator(cfg, indicator_ref=MagicMock())
    ind.set_state(State.RUNNING)
    assert (Path(cfg.state_path).expanduser()).read_text().strip() == "running"


def test_set_state_writes_log(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    ind = Indicator(cfg, indicator_ref=MagicMock())
    ind.set_state(State.RUNNING)
    log_contents = ind.log_path.read_text()
    assert "state -> running" in log_contents


def test_icon_path_uses_size(tmp_path: Path) -> None:
    (tmp_path / "thing-running-64.png").write_bytes(b"")
    cfg = _make_config(tmp_path)
    ind = Indicator(cfg, indicator_ref=MagicMock())
    assert ind.icon_path(State.RUNNING) == tmp_path / "thing-running-64.png"


def test_icon_path_falls_back(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    (tmp_path / "thing-circle-64.png").write_bytes(b"")
    ind = Indicator(cfg, indicator_ref=MagicMock())
    # No per-state icon → fallback
    assert ind.icon_path(State.RUNNING) == tmp_path / "thing-circle-64.png"


def test_log_creates_parent_dir(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    # Default log path is ~/.cache/hermes-thing.log
    ind = Indicator(cfg, indicator_ref=MagicMock())
    ind.log("test message")
    assert ind.log_path.exists()
    assert "test message" in ind.log_path.read_text()


def test_swap_icon_dispatches_via_glib(tmp_path: Path) -> None:
    (tmp_path / "thing-circle-64.png").write_bytes(b"")
    (tmp_path / "thing-running-64.png").write_bytes(b"")
    cfg = _make_config(tmp_path)
    mock_ref = MagicMock()
    ind = Indicator(cfg, indicator_ref=mock_ref)

    # Mock gi.repository.GLib as a module (gi may not be importable on
    # headless test runners — the lib doesn't depend on PyGObject for tests).
    fake_glib = MagicMock()
    fake_repo = MagicMock()
    fake_repo.GLib = fake_glib
    fake_gi = MagicMock()
    fake_gi.repository = fake_repo

    import sys as _sys

    saved = {k: _sys.modules.get(k) for k in ("gi", "gi.repository")}
    _sys.modules["gi"] = fake_gi
    _sys.modules["gi.repository"] = fake_repo
    try:
        ind.swap_icon(State.RUNNING)
    finally:
        for k, v in saved.items():
            if v is None:
                _sys.modules.pop(k, None)
            else:
                _sys.modules[k] = v

    fake_glib.idle_add.assert_called_once()
    # First positional arg is the bound method
    assert fake_glib.idle_add.call_args[0][0] == mock_ref.set_icon_full
