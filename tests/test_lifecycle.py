"""Tests for the lifecycle functions (start, stop, restart)."""

from __future__ import annotations

import threading
import time
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hermes_tray import Config, Indicator, State
from hermes_tray.lifecycle import restart, start, stop


@pytest.fixture
def config(tmp_path: Path) -> Config:
    (tmp_path / "thing-circle-64.png").write_bytes(b"")
    return Config(
        name="thing",
        title="T",
        bin="thing",
        subcommand=("serve",),
        host="h",
        port=1,
        url="u",
        icon_dir=tmp_path,
        icon_fallback="thing-circle-64.png",
    )


@pytest.fixture
def indicator(config: Config) -> Indicator:
    return Indicator(config, indicator_ref=MagicMock())


def test_start_uses_configured_cwd(config: Config, indicator: Indicator, tmp_path: Path) -> None:
    config = replace(config, cwd=str(tmp_path))
    with patch("subprocess.Popen") as mock_popen:
        start(config, indicator)
        args, kwargs = mock_popen.call_args
        assert kwargs["cwd"] == str(tmp_path)


def test_start_marks_error_on_popen_failure(config: Config, indicator: Indicator) -> None:
    with patch("subprocess.Popen", side_effect=OSError("boom")):
        start(config, indicator)
    assert indicator.current is State.ERROR


def test_start_sets_starting_state(config: Config, indicator: Indicator) -> None:
    with patch("subprocess.Popen"):
        start(config, indicator)
    assert indicator.current is State.STARTING


def test_stop_runs_pkill(config: Config, indicator: Indicator) -> None:
    with patch("subprocess.run") as mock_run:
        stop(config, indicator)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "pkill"
        # The pkill -f flag takes the needle as a single string
        assert "thing" in cmd[2]
        assert "--host" in cmd[2]
        assert "h" in cmd[2]


def test_stop_sets_stopped_state(config: Config, indicator: Indicator) -> None:
    with patch("subprocess.run"):
        stop(config, indicator)
    assert indicator.current is State.STOPPED


def test_restart_sets_lock_and_spawns_thread(config: Config, indicator: Indicator) -> None:
    lock = Path(config.restart_lock_path).expanduser()
    # Pre-cleanup
    if lock.exists():
        lock.unlink()

    started = threading.Event()

    real_thread_init = threading.Thread.__init__

    def patched_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        real_thread_init(self, *args, **kwargs)
        started.set()

    with patch.object(threading.Thread, "__init__", patched_init):
        restart(config, indicator)
        assert started.wait(timeout=1.0), "restart thread was not spawned"
        # Lock is set immediately
        assert lock.exists()


def test_restart_short_circuits_when_already_in_progress(
    config: Config, indicator: Indicator
) -> None:
    # Manually create the lock
    lock = Path(config.restart_lock_path).expanduser()
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.touch()
    try:
        with patch.object(threading.Thread, "start") as mock_start:
            restart(config, indicator)
            mock_start.assert_not_called()
    finally:
        lock.unlink()


def test_restart_thread_eventually_clears_lock(config: Config, indicator: Indicator) -> None:
    lock = Path(config.restart_lock_path).expanduser()
    if lock.exists():
        lock.unlink()

    # Speed up the restart by using a tiny delay
    config = replace(config, restart_delay=0)

    with patch("subprocess.Popen"), patch("subprocess.run"):
        restart(config, indicator)
        # Wait for the thread to finish
        time.sleep(0.5)
        assert not lock.exists()
