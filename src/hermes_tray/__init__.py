"""hermes-tray-lib: shared infrastructure for Hermes-* tray indicators.

This package provides the common building blocks every Linux GNOME tray
indicator in the Hermes family needs: AppIndicator3 setup, a state machine,
status-aware icon swapping, a watcher thread, a right-click menu, and the
top-level entry point. Specific indicators (the Hermes dashboard, the
Mnemosyne dashboard, the Hermes router) are thin wrappers that supply a
``Config`` and a ``LivenessProbe`` and call :func:`main`.

Public API
----------

Classes
~~~~~~~

- :class:`Config` — immutable, env-driven configuration (frozen dataclass).
- :class:`State` — lifecycle enum (``RUNNING`` / ``STARTING`` / ``STOPPED`` /
  ``RESTARTING`` / ``ERROR``).
- :class:`LivenessProbe` — abstract base for liveness checks.
- :class:`PortListeningProbe` — probe that succeeds on TCP connect.
- :class:`ProcessCommandProbe` — probe that succeeds when ``ps`` output
  contains a needle.
- :class:`UrlHealthProbe` — probe that succeeds on HTTP 2xx.
- :class:`Indicator` — state holder + icon-swap coordinator (thread-safe).

Functions
~~~~~~~~~

- :func:`build_menu` — construct the right-click menu and return
  ``(menu, status_item)``.
- :func:`run_watcher` — the watcher thread body (also exported as
  :func:`watcher.run`).
- :func:`start`, :func:`stop`, :func:`restart` — subprocess lifecycle.
- :func:`main` — the top-level entry point: builds the indicator, the menu,
  the watcher, and enters ``Gtk.main()``.

Example
-------

Minimal custom tray (no library state, just the boilerplate)::

    from pathlib import Path
    from hermes_tray import Config, LivenessProbe, main

    class MyProbe(LivenessProbe):
        def alive(self) -> bool:
            return True

    cfg = Config(
        name="mything",
        title="My Thing",
        bin="mything",
        subcommand=("serve",),
        host="localhost",
        port=8080,
        url="http://localhost:8080",
        icon_dir=Path("~/.local/share/icons/hicolor/256x256/apps").expanduser(),
        icon_fallback="mything-circle-64.png",
    )
    main(cfg, MyProbe())
"""

from __future__ import annotations

import logging
import subprocess
import sys
import threading

from hermes_tray import lifecycle, watcher
from hermes_tray.config import Config
from hermes_tray.indicator import Indicator
from hermes_tray.lifecycle import restart, start, stop
from hermes_tray.liveness import (
    LivenessProbe,
    PortListeningProbe,
    ProcessCommandProbe,
    UrlHealthProbe,
)
from hermes_tray.menu import build_menu
from hermes_tray.state import State
from hermes_tray.watcher import run as run_watcher

# Re-export the lifecycle module so callers can `hermes_tray.lifecycle.foo`
# while we also expose the top-level functions in `hermes_tray.*`.
__all__ = [
    "Config",
    "Indicator",
    "LivenessProbe",
    "PortListeningProbe",
    "ProcessCommandProbe",
    "State",
    "UrlHealthProbe",
    "build_menu",
    "lifecycle",
    "main",
    "restart",
    "run_watcher",
    "start",
    "stop",
    "watcher",
]

__version__ = "0.1.1"

_LOGGER = logging.getLogger(__name__)


def _open_url(cfg: Config) -> None:
    try:
        subprocess.Popen(
            [cfg.browser_cmd, cfg.url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        _LOGGER.warning("browser command not found: %s", cfg.browser_cmd)


def _quit(cfg: Config, ind: Indicator) -> None:
    ind.log("indicator quit")
    sys.exit(0)


def main(cfg: Config, probe: LivenessProbe) -> int:
    """Top-level entry point for a tray indicator.

    Builds the AppIndicator3 indicator, the right-click menu, the watcher
    thread, and enters ``Gtk.main()``. Returns when the user picks
    "Quit Indicator" from the menu.

    Args:
        cfg: a :class:`Config` for the indicator. Env-var overrides are
             applied at construction time.
        probe: a :class:`LivenessProbe` used by the watcher to keep the
               indicator's state in sync with the supervised subprocess.

    Returns:
        The process exit code (0 on a clean quit).
    """
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3, GLib, Gtk

    ind_ref = AppIndicator3.Indicator.new(
        cfg.name,
        str(cfg.icon_fallback_path),
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    ind_ref.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
    ind_ref.set_title(cfg.title)
    indicator = Indicator(cfg, ind_ref)

    def refresh_status(_state: State | None = None) -> bool:
        item_status.set_label(f"Status: {indicator.current.value}")
        return True

    menu, item_status = build_menu(
        cfg,
        ind_ref,
        on_start=lambda: start(cfg, indicator),
        on_stop=lambda: stop(cfg, indicator),
        on_restart=lambda: restart(cfg, indicator),
        on_open=lambda: _open_url(cfg),
        on_quit=lambda: _quit(cfg, indicator),
    )
    ind_ref.set_menu(menu)

    if cfg.auto_start:
        start(cfg, indicator)

    GLib.timeout_add(1000, refresh_status)
    threading.Thread(
        target=watcher.run,
        args=(indicator, probe, refresh_status),
        daemon=True,
    ).start()
    Gtk.main()
    return 0
