"""Tests for the menu builder (smoke only — GTK is hard to mock)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from hermes_tray import Config
from hermes_tray.menu import build_menu


def test_build_menu_smoke(tmp_path: Path) -> None:
    cfg = Config(
        name="thing",
        title="T",
        bin="t",
        subcommand=("s",),
        host="h",
        port=1,
        url="u",
        icon_dir=tmp_path,
        icon_fallback="f",
    )

    # Mock out gi + Gtk so we can run headless
    fake_gtk_menu = MagicMock()
    fake_gtk_menu_item = MagicMock()
    fake_separator = MagicMock()
    fake_gtk_module = MagicMock()
    fake_gtk_module.Menu = MagicMock(return_value=fake_gtk_menu)
    fake_gtk_module.MenuItem = MagicMock(return_value=fake_gtk_menu_item)
    fake_gtk_module.SeparatorMenuItem = MagicMock(return_value=fake_separator)
    fake_gi = MagicMock()
    fake_gi.require_version = MagicMock()

    fake_repo = MagicMock()
    fake_repo.Gtk = fake_gtk_module

    with patch.dict("sys.modules", {"gi": fake_gi, "gi.repository": fake_repo}):
        menu, status = build_menu(
            cfg,
            MagicMock(),
            on_start=lambda: None,
            on_stop=lambda: None,
            on_restart=lambda: None,
            on_open=lambda: None,
            on_quit=lambda: None,
        )

    # Just verify we got objects back and the menu was populated
    assert menu is fake_gtk_menu
    assert status is fake_gtk_menu_item
    assert (
        fake_gtk_menu.append.call_count >= 7
    )  # status, open, sep, start, stop, restart, sep, quit
