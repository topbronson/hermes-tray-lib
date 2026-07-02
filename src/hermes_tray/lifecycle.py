"""Start, stop, and restart the supervised subprocess.

All three functions are safe to call from any thread; :func:`restart` itself
spawns a worker thread so the menu call returns immediately.
"""

from __future__ import annotations

import contextlib
import subprocess
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

from hermes_tray.state import State

if TYPE_CHECKING:
    from hermes_tray.config import Config
    from hermes_tray.indicator import Indicator


def _resolve_cwd(config: Config) -> str:
    """Return the supervised subprocess's working directory.

    Falls back to ``$HOME`` if the configured path doesn't exist (e.g. a
    user-specific project dir that hasn't been created yet).
    """
    cwd = Path(config.cwd).expanduser()
    if cwd.is_dir():
        return str(cwd)
    return str(Path.home())


def start(config: Config, ind: "Indicator") -> None:
    """Spawn the supervised subprocess.

    Sets state to :attr:`State.STARTING` on success, or
    :attr:`State.ERROR` if ``Popen`` raises. The watcher thread will
    later promote ``STARTING`` to :attr:`State.RUNNING` once the
    liveness probe passes.
    """
    try:
        with ind.log_path.open("a", buffering=1) as fh:
            subprocess.Popen(
                config.cmd,
                stdout=fh,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                cwd=_resolve_cwd(config),
            )
        ind.log(f"launched (cmd={config.cmd})")
        ind.set_state(State.STARTING)
    except OSError as exc:
        ind.log(f"failed to launch: {exc}")
        ind.set_state(State.ERROR)


def stop(config: Config, ind: "Indicator") -> None:
    """``pkill`` the supervised subprocess. Idempotent.

    Matches on the full ``bin + subcommand + --host <host>`` string, which
    is unique to this indicator. The match is best-effort: if the process
    is already gone, ``pkill`` exits non-zero and we ignore it.
    """
    needle = " ".join([config.bin, *config.subcommand, "--host", config.host])
    subprocess.run(["pkill", "-f", needle], check=False)
    ind.set_state(State.STOPPED)
    ind.log("stopped")


def _is_restarting(config: Config) -> bool:
    return Path(config.restart_lock_path).expanduser().exists()


def _set_restarting(config: Config, flag: bool) -> None:
    path = Path(config.restart_lock_path).expanduser()
    if flag:
        path.touch()
    else:
        with contextlib.suppress(FileNotFoundError):
            path.unlink()


def restart(config: Config, ind: "Indicator") -> None:
    """Stop, wait, start. Returns immediately; runs in a background thread.

    The restart lock file is set before the thread spawns, so a rapid
    second click on Restart finds the lock already held and short-circuits
    instead of spawning a second restart thread that races the first on
    the port.
    """
    if _is_restarting(config):
        ind.log("restart: already in progress, ignoring re-entry")
        return
    _set_restarting(config, True)
    ind.set_state(State.STARTING)

    def _do() -> None:
        ind.log("restart: stopping")
        stop(config, ind)
        ind.log(f"restart: sleeping {config.restart_delay}s for port release")
        time.sleep(config.restart_delay)
        ind.log("restart: starting")
        start(config, ind)
        _set_restarting(config, False)

    threading.Thread(target=_do, daemon=True).start()
