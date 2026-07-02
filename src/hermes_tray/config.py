"""Immutable, env-driven configuration for a Hermes-* tray indicator.

:class:`Config` is built once at indicator startup. Any environment variables
matching the indicator's prefix (``HERMES_<NAME>_*``) are read at construction
time and override the defaults passed in. Once constructed, the config is
frozen — passing it around is safe, mutating it is not.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def _env_str(name: str, default: str) -> str:
    """Return the env var if set, otherwise the default."""
    val = os.environ.get(name)
    return val if val is not None else default


def _env_int(name: str, default: int) -> int:
    """Return the env var parsed as an int, otherwise the default.

    Returns the default on missing value, empty string, or a non-integer value.
    """
    val = os.environ.get(name)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    """Return the env var interpreted as a bool, otherwise the default.

    Truthy values are ``1``, ``true``, ``yes``, ``on`` (case-insensitive).
    """
    val = os.environ.get(name)
    if val is None or val == "":
        return default
    return val.lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True, slots=True)
class Config:
    """Immutable configuration for one tray indicator.

    Attributes:
        name: short identifier used for env-var prefix and the systemd unit
              name. Must be lowercase, alphanumeric + hyphens. Env vars are
              derived as ``HERMES_{name.upper().replace('-', '_')}_*``.
        title: human-readable title shown in the tray menu and tooltip.
        bin: PATH-relative (or absolute) path to the binary the indicator
             supervises. The indicator will refuse to start if this is not
             on PATH (it doesn't error at construction — only at start).
        subcommand: tuple of subcommand + flags to invoke. The constructed
             subprocess command is
             ``[bin, *subcommand, --host, host, --port, port]``.
        host: bind host. Read from ``HERMES_<NAME>_HOST`` env var.
        port: bind port (1-65535). Read from ``HERMES_<NAME>_PORT`` env var.
        url: URL opened by the "Open" menu item. Read from
             ``HERMES_<NAME>_URL`` env var.
        icon_dir: directory where per-state and circle icons are stored.
        icon_fallback: filename inside ``icon_dir`` of the default icon
                       (used at startup and when a per-state icon is missing).
        cwd: working directory of the supervised subprocess. Falls back to
             ``$HOME`` if the configured path doesn't exist.
        restart_delay: seconds to wait between stop and start on restart.
        auto_start: whether to start the subprocess on indicator launch.
        browser_cmd: command to open URLs (typically ``xdg-open``).
        log_path: where the indicator writes its log.
        state_path: where the current state is persisted.
        restart_lock_path: sentinel file present during restart.
    """

    name: str
    title: str
    bin: str
    subcommand: Sequence[str]
    host: str
    port: int
    url: str
    icon_dir: Path
    icon_fallback: str

    cwd: str = "~"
    restart_delay: int = 5
    auto_start: bool = True
    browser_cmd: str = "xdg-open"
    log_path: str = ""
    state_path: str = ""
    restart_lock_path: str = ""

    def __post_init__(self) -> None:
        # Validate name: lowercase, alphanumeric, hyphens
        if (
            not self.name
            or not all(c.isalnum() or c == "-" for c in self.name)
            or self.name != self.name.lower()
        ):
            raise ValueError(f"name must be lowercase alphanumeric/hyphens, got {self.name!r}")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"port must be 1-65535, got {self.port}")
        if not self.subcommand:
            raise ValueError("subcommand must be non-empty")
        if not self.icon_fallback:
            raise ValueError("icon_fallback must be non-empty")

        # Freeze subcommand to a tuple so the dataclass is hashable
        if not isinstance(self.subcommand, tuple):
            object.__setattr__(self, "subcommand", tuple(self.subcommand))

        # Expand icon_dir
        object.__setattr__(self, "icon_dir", self.icon_dir.expanduser())

        # Apply env-var overrides (name is validated so this is safe)
        prefix = self.env_prefix()
        object.__setattr__(self, "host", _env_str(prefix + "HOST", self.host))
        object.__setattr__(self, "port", _env_int(prefix + "PORT", self.port))
        object.__setattr__(self, "url", _env_str(prefix + "URL", self.url))
        object.__setattr__(self, "cwd", _env_str(prefix + "CWD", self.cwd))
        object.__setattr__(
            self, "restart_delay", _env_int(prefix + "RESTART_DELAY", self.restart_delay)
        )
        object.__setattr__(self, "auto_start", _env_bool(prefix + "AUTO_START", self.auto_start))
        object.__setattr__(self, "browser_cmd", _env_str(prefix + "BROWSER_CMD", self.browser_cmd))

        # Default log/state/lock paths
        if not self.log_path:
            object.__setattr__(self, "log_path", f"~/.cache/hermes-{self.name}.log")
        if not self.state_path:
            object.__setattr__(self, "state_path", f"~/.cache/hermes-{self.name}.state")
        if not self.restart_lock_path:
            object.__setattr__(self, "restart_lock_path", f"~/.cache/hermes-{self.name}.restart")

    @property
    def icon_fallback_path(self) -> Path:
        """The full on-disk path of the default icon."""
        return self.icon_dir / self.icon_fallback

    @property
    def cmd(self) -> list[str]:
        """The full subprocess command (no extra flags)."""
        return [self.bin, *self.subcommand, "--host", self.host, "--port", str(self.port)]

    def env_prefix(self) -> str:
        """Return the env-var prefix this config reads from."""
        return f"HERMES_{self.name.upper().replace('-', '_')}_"
