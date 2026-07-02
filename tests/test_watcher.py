"""Tests for the watcher thread."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hermes_tray import (
    Config,
    Indicator,
    LivenessProbe,
    State,
)
from hermes_tray.watcher import run


@pytest.fixture
def config(tmp_path: Path) -> Config:
    (tmp_path / "thing-circle-64.png").write_bytes(b"")
    return Config(
        name="thing",
        title="T",
        bin="t",
        subcommand=("s",),
        host="h",
        port=1,
        url="u",
        icon_dir=tmp_path,
        icon_fallback="thing-circle-64.png",
    )


class AlwaysAlive(LivenessProbe):
    def alive(self) -> bool:
        return True


class AlwaysDead(LivenessProbe):
    def alive(self) -> bool:
        return False


def test_watcher_promotes_to_running(config: Config) -> None:
    ind = Indicator(config, indicator_ref=MagicMock())
    refreshes: list[State] = []
    run(ind, AlwaysAlive(), refresh_status=refreshes.append, poll_interval=0.0, iterations=2)
    assert ind.current is State.RUNNING
    assert refreshes == [State.RUNNING]


def test_watcher_demotes_to_stopped(config: Config) -> None:
    ind = Indicator(config, indicator_ref=MagicMock())
    ind.set_state(State.RUNNING)  # start from running
    refreshes: list[State] = []
    run(ind, AlwaysDead(), refresh_status=refreshes.append, poll_interval=0.0, iterations=2)
    assert ind.current is State.STOPPED
    assert refreshes == [State.STOPPED]


def test_watcher_skips_during_restart_lock(config: Config) -> None:
    ind = Indicator(config, indicator_ref=MagicMock())
    lock = Path(config.restart_lock_path).expanduser()
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.touch()
    try:
        refreshes: list[State] = []
        # Alive probe but lock present → no state change
        run(ind, AlwaysAlive(), refresh_status=refreshes.append, poll_interval=0.0, iterations=2)
        assert ind.current is State.STOPPED
        assert refreshes == []
    finally:
        lock.unlink()


def test_watcher_swallows_refresh_callback_exception(config: Config) -> None:
    ind = Indicator(config, indicator_ref=MagicMock())

    def bad_refresh(_state: State) -> None:
        raise RuntimeError("boom")

    # Should not raise
    run(ind, AlwaysAlive(), refresh_status=bad_refresh, poll_interval=0.0, iterations=2)
    assert ind.current is State.RUNNING


def test_watcher_does_not_emit_duplicate_state_changes(config: Config) -> None:
    ind = Indicator(config, indicator_ref=MagicMock())
    refreshes: list[State] = []
    # Many iterations, same probe state → only one refresh
    run(ind, AlwaysAlive(), refresh_status=refreshes.append, poll_interval=0.0, iterations=10)
    assert refreshes == [State.RUNNING]
