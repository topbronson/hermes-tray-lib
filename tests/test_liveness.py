"""Tests for the LivenessProbe implementations."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from hermes_tray import (
    LivenessProbe,
    PortListeningProbe,
    ProcessCommandProbe,
    UrlHealthProbe,
)


def test_abstract_cannot_instantiate() -> None:
    with pytest.raises(TypeError):
        LivenessProbe()  # type: ignore[abstract]


def test_port_listening_returns_true_when_socket_connectable() -> None:
    with patch("socket.create_connection") as mock_conn:
        mock_conn.return_value.__enter__.return_value = None
        probe = PortListeningProbe(host="localhost", port=8319)
        assert probe.alive() is True
        mock_conn.assert_called_once_with(("localhost", 8319), timeout=1.0)


def test_port_listening_returns_false_on_oserror() -> None:
    with patch("socket.create_connection") as mock_conn:
        mock_conn.side_effect = OSError("refused")
        probe = PortListeningProbe(host="localhost", port=8319)
        assert probe.alive() is False


def test_process_command_matches_needle() -> None:
    probe = ProcessCommandProbe(needle="python router.py")
    fake_ps = (
        "PID COMM ARGS\n"
        "  1 init /sbin/init\n"
        "100 python python router.py --host 0.0.0.0 --port 8319\n"
    )
    with patch("subprocess.check_output", return_value=fake_ps):
        assert probe.alive() is True


def test_process_command_no_match() -> None:
    probe = ProcessCommandProbe(needle="python router.py")
    fake_ps = "PID COMM ARGS\n1 init /sbin/init\n"
    with patch("subprocess.check_output", return_value=fake_ps):
        assert probe.alive() is False


def test_process_command_excludes_indicator_by_default() -> None:
    probe = ProcessCommandProbe(needle="python")
    fake_ps = "PID COMM ARGS\n  1 python /usr/bin/python3 indicator.py\n"
    with patch("subprocess.check_output", return_value=fake_ps):
        assert probe.alive() is False


def test_process_command_includes_indicator_when_disabled() -> None:
    probe = ProcessCommandProbe(needle="python", exclude_indicator=False)
    fake_ps = "PID COMM ARGS\n1 python /usr/bin/python3 indicator.py\n"
    with patch("subprocess.check_output", return_value=fake_ps):
        assert probe.alive() is True


def test_process_command_subprocess_failure() -> None:
    probe = ProcessCommandProbe(needle="x")
    with patch("subprocess.check_output", side_effect=OSError("ps failed")):
        assert probe.alive() is False


def test_url_health_returns_true_on_2xx() -> None:
    probe = UrlHealthProbe(url="http://localhost:8319/health")
    fake_resp = type("R", (), {"status": 200})()
    fake_resp_ctx = type(
        "Ctx", (), {"__enter__": lambda s: fake_resp, "__exit__": lambda *a: None}
    )()
    with patch("hermes_tray.liveness.urlopen", return_value=fake_resp_ctx):
        assert probe.alive() is True


def test_url_health_returns_false_on_5xx() -> None:
    probe = UrlHealthProbe(url="http://localhost:8319/health")
    fake_resp = type("R", (), {"status": 500})()
    fake_resp_ctx = type(
        "Ctx", (), {"__enter__": lambda s: fake_resp, "__exit__": lambda *a: None}
    )()
    with patch("hermes_tray.liveness.urlopen", return_value=fake_resp_ctx):
        assert probe.alive() is False


def test_url_health_returns_false_on_exception() -> None:
    probe = UrlHealthProbe(url="http://localhost:8319/health")
    with patch("hermes_tray.liveness.urlopen", side_effect=OSError("refused")):
        assert probe.alive() is False
