"""Shared pytest fixtures for the hermes-tray-lib test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_tray import Config


@pytest.fixture
def icon_dir(tmp_path: Path) -> Path:
    """An empty icon directory."""
    return tmp_path


@pytest.fixture
def basic_config(icon_dir: Path) -> Config:
    """A minimal valid Config for tests."""
    return Config(
        name="thing",
        title="Thing",
        bin="thing",
        subcommand=("serve",),
        host="localhost",
        port=8080,
        url="http://localhost:8080",
        icon_dir=icon_dir,
        icon_fallback="thing-circle-64.png",
    )
