"""Lifecycle state of the supervised subprocess.

State transitions are driven by three sources:

1. User actions (Start / Stop / Restart menu items).
2. The watcher thread (alive check → RUNNING / STOPPED).
3. Errors during start/stop (caught and mapped to ERROR).

The state machine is intentionally trivial — a single ``current: State``
attribute on :class:`hermes_tray.Indicator`. No fancy transition validation;
the watcher is the source of truth.
"""

from __future__ import annotations

from enum import Enum


class State(Enum):
    """The lifecycle state of the supervised subprocess.

    Attributes:
        RUNNING: subprocess is up and the liveness check passes.
        STARTING: subprocess was just spawned; waiting for it to come up.
        STOPPED: subprocess is not running.
        RESTARTING: subprocess is being stopped and will be started again.
                    Visually identical to STARTING.
        ERROR: subprocess is not running AND the last attempt to start it
               failed.
    """

    RUNNING = "running"
    STARTING = "starting"
    STOPPED = "stopped"
    RESTARTING = "restarting"
    ERROR = "error"

    @property
    def icon_filename(self) -> str:
        """Base filename (without size suffix) for this state's icon.

        ``RESTARTING`` reuses the ``starting`` icon since the visual cue
        (yellow dot) is the same.
        """
        if self is State.RESTARTING:
            return "starting"
        return str(self.value)

    @property
    def dot_color(self) -> tuple[int, int, int, int]:
        """RGBA color of the status-dot overlay for this state."""
        match self:
            case State.RUNNING:
                return (60, 162, 60, 255)  # green
            case State.STARTING | State.RESTARTING:
                return (220, 180, 40, 255)  # yellow
            case State.STOPPED:
                return (140, 140, 140, 255)  # grey
            case State.ERROR:
                return (200, 50, 50, 255)  # red

    @property
    def label(self) -> str:
        """Human-readable label, used in tooltips and menu."""
        return str(self.value)
