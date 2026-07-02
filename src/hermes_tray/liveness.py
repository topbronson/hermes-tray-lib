"""Liveness probes for supervised subprocesses.

A :class:`LivenessProbe` is a single-method object (``alive() -> bool``) the
watcher's hot loop calls every couple of seconds. Three built-in probes
cover the common patterns; users can subclass :class:`LivenessProbe` for
anything else (HTTP health check, PID file, DB query, etc.).

All probes are designed to be safe to call frequently: they must complete
quickly, never raise, and never mutate external state.
"""

from __future__ import annotations

import socket
import subprocess
from abc import ABC, abstractmethod
from urllib.request import urlopen


class LivenessProbe(ABC):
    """Abstract base class for liveness checks."""

    @abstractmethod
    def alive(self) -> bool:
        """Return ``True`` iff the supervised subprocess is healthy."""


class PortListeningProbe(LivenessProbe):
    """Probe that succeeds when a TCP port is accepting connections."""

    __slots__ = ("host", "port", "timeout")

    def __init__(self, host: str, port: int, timeout: float = 1.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def alive(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout):
                return True
        except OSError:
            return False


class ProcessCommandProbe(LivenessProbe):
    """Probe that succeeds when ``ps`` output contains a needle.

    The needle is matched as a substring of each ``ps`` line's command+args.
    By default the check ignores the indicator's own process by filtering
    out lines that contain the word ``indicator``.
    """

    __slots__ = ("exclude_indicator", "needle")

    def __init__(self, needle: str, *, exclude_indicator: bool = True) -> None:
        self.needle = needle
        self.exclude_indicator = exclude_indicator

    def alive(self) -> bool:
        try:
            out = subprocess.check_output(
                ["ps", "-eo", "comm,args"],
                text=True,
                errors="ignore",
            )
        except (OSError, subprocess.SubprocessError):
            return False
        for line in out.splitlines():
            if self.exclude_indicator and "indicator" in line:
                continue
            if self.needle in line:
                return True
        return False


class UrlHealthProbe(LivenessProbe):
    """Probe that succeeds when an HTTP health endpoint returns 2xx."""

    __slots__ = ("timeout", "url")

    def __init__(self, url: str, timeout: float = 2.0) -> None:
        self.url = url
        self.timeout = timeout

    def alive(self) -> bool:
        try:
            with urlopen(self.url, timeout=self.timeout) as resp:
                status: int = resp.status
                return 200 <= status < 300
        except Exception:  # any failure means "not alive"
            return False


__all__ = [
    "LivenessProbe",
    "PortListeningProbe",
    "ProcessCommandProbe",
    "UrlHealthProbe",
]
