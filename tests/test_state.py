"""Tests for the State enum."""

from __future__ import annotations

from hermes_tray import State


def test_states_are_distinct() -> None:
    # Compare via id() to silence mypy's literal-overlap warning while
    # still proving the states are distinct objects.
    states = [State.RUNNING, State.STOPPED, State.STARTING, State.ERROR, State.RESTARTING]
    assert len(states) == len(set(map(id, states)))


def test_icon_filename() -> None:
    assert State.RUNNING.icon_filename == "running"
    assert State.STOPPED.icon_filename == "stopped"
    assert State.STARTING.icon_filename == "starting"
    assert State.ERROR.icon_filename == "error"
    # RESTARTING reuses the starting icon (same yellow dot)
    assert State.RESTARTING.icon_filename == "starting"


def test_dot_color_is_rgba() -> None:
    for state in State:
        color = state.dot_color
        assert isinstance(color, tuple)
        assert len(color) == 4
        assert all(0 <= c <= 255 for c in color)


def test_running_is_green() -> None:
    r, g, b, a = State.RUNNING.dot_color
    assert g > r and g > b
    assert a == 255


def test_error_is_red() -> None:
    r, g, b, a = State.ERROR.dot_color
    assert r > g and r > b
    assert a == 255


def test_label() -> None:
    assert State.RUNNING.label == "running"
    assert State.STOPPED.label == "stopped"
    assert State.STARTING.label == "starting"
    assert State.ERROR.label == "error"
    assert State.RESTARTING.label == "restarting"
