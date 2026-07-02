"""The :class:`Indicator` class: state, icon-swap, log-and-persist.

``Indicator`` wraps the AppIndicator3 reference (passed in from the entry
point, since creating one requires a live GTK main loop) and provides a
clean interface for the lifecycle/watcher code::

    ind.set_state(State.RUNNING)        # writes state file + swaps icon
    ind.current                        # -> State
    ind.icon_path(State.X)              # -> Path
    ind.log("started")                  # append-only log

All icon-swap calls are dispatched to the GTK main thread via
``GLib.idle_add``, which is mandatory for thread safety with AppIndicator3.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from hermes_tray.state import State

if TYPE_CHECKING:
    from hermes_tray.config import Config


class _IndicatorRef(Protocol):
    """Minimal interface we need from an AppIndicator3 indicator."""

    def set_icon_full(self, icon_name: str, desc: str) -> None: ...


_LOGGER = logging.getLogger(__name__)


class Indicator:
    """State holder + icon-swap coordinator for one tray indicator.

    Constructed at startup with a reference to the live AppIndicator3
    indicator. All public methods are thread-safe; icon swaps are
    dispatched to the GTK main thread.
    """

    def __init__(self, config: Config, indicator_ref: _IndicatorRef) -> None:
        self._config = config
        self._indicator_ref = indicator_ref
        self._state: State = State.STOPPED
        self._log_path = Path(config.log_path).expanduser()
        self._state_path = Path(config.state_path).expanduser()
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def current(self) -> State:
        """The current state (defaults to :attr:`State.STOPPED`)."""
        return self._state

    @property
    def config(self) -> Config:
        """The :class:`Config` this indicator was built with."""
        return self._config

    @property
    def log_path(self) -> Path:
        """The on-disk log file path (expanded)."""
        return self._log_path

    def log(self, msg: str) -> None:
        """Append a timestamped line to the indicator log.

        Failures are logged via Python's logging facility but never raised
        — logging should be best-effort and never crash the indicator.
        """
        try:
            with self._log_path.open("a", buffering=1) as fh:
                fh.write(f"[{time.strftime('%F %T')}] {msg}\n")
        except OSError as exc:
            _LOGGER.warning("log write failed: %s", exc)

    def set_state(self, state: State) -> None:
        """Persist the state, swap the icon, update the tooltip."""
        self._state = state
        try:
            self._state_path.write_text(state.value)
        except OSError as exc:
            self.log(f"set_state({state.value}) failed: {exc}")
        self.swap_icon(state)
        self.log(f"state -> {state.value}")

    def icon_path(self, state: State) -> Path:
        """Resolve the on-disk path for a state's icon.

        Falls back to :attr:`Config.icon_fallback_path` if the per-state
        icon doesn't exist on disk yet (e.g. icons haven't been generated).
        """
        name = f"{self._config.name}-{state.icon_filename}-64.png"
        candidate = self._config.icon_dir / name
        if candidate.exists():
            return candidate
        return self._config.icon_fallback_path

    def swap_icon(self, state: State) -> None:
        """Swap the tray icon (and tooltip) to reflect a state.

        Thread-safe: the actual AppIndicator3 call is dispatched to the
        GTK main thread via ``GLib.idle_add``.
        """
        icon_path = str(self.icon_path(state))
        title = f"{self._config.title} ({state.label})"
        try:
            from gi.repository import GLib
        except ImportError:
            self.log("GLib not available, skipping icon swap")
            return
        try:
            GLib.idle_add(self._indicator_ref.set_icon_full, icon_path, title)
        except Exception as exc:  # GTK calls can raise anything
            self.log(f"icon swap failed: {exc}")
