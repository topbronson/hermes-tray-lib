"""Background thread that polls the liveness probe and keeps state in sync.

This module exposes a single :func:`run` function intended to be called
inside a daemon thread. The watcher's hot loop is intentionally tiny so
it's easy to reason about:

    while not lock.exists():
        state = RUNNING if probe.alive() else STOPPED
        if state changed: ind.set_state(state); refresh_status(state)
        sleep(poll_interval)
"""

from __future__ import annotations

import contextlib
import time
from pathlib import Path
from typing import TYPE_CHECKING

from hermes_tray.state import State

if TYPE_CHECKING:
    from collections.abc import Callable

    from hermes_tray.indicator import Indicator
    from hermes_tray.liveness import LivenessProbe


def run(
    ind: "Indicator",
    probe: "LivenessProbe",
    refresh_status: "Callable[[State], None]",
    poll_interval: float = 2.0,
    iterations: int | None = None,
) -> None:
    """Poll ``probe.alive()`` every ``poll_interval`` seconds.

    Updates :attr:`Indicator.current` and the icon. Skips observation
    while a restart lock file is present (the restart thread owns the
    state during that window). Intended to be called in a daemon thread.

    Args:
        ind: the indicator to update.
        probe: the liveness probe.
        refresh_status: callback fired on each state change (typically
            the menu's "Status: …" item updater).
        poll_interval: seconds between polls.
        iterations: if set, run for this many iterations and return.
            Used by tests to avoid an infinite loop.
    """
    lock = Path(ind.config.restart_lock_path).expanduser()
    last: State | None = None
    count = 0
    while iterations is None or count < iterations:
        if not lock.exists():
            alive = probe.alive()
            state = State.RUNNING if alive else State.STOPPED
            if state != last:
                ind.set_state(state)
                with contextlib.suppress(Exception):  # best-effort UI callback
                    refresh_status(state)
                last = state
        time.sleep(poll_interval)
        count += 1
