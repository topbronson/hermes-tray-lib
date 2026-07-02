"""Build the right-click menu for a tray indicator.

GTK imports are deferred to this function so the rest of the library can be
imported and tested in headless environments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

    from hermes_tray.config import Config


class _MenuItemLike(Protocol):
    """Minimal interface we need from a Gtk.MenuItem — has set_label()."""

    def set_label(self, label: str) -> None: ...
    def set_sensitive(self, sensitive: bool) -> None: ...
    def connect(self, signal: str, handler: object) -> None: ...


def build_menu(
    config: Config,
    indicator_ref: object,
    *,
    on_start: "Callable[[], None]",
    on_stop: "Callable[[], None]",
    on_restart: "Callable[[], None]",
    on_open: "Callable[[], None]",
    on_quit: "Callable[[], None]",
) -> tuple[object, _MenuItemLike]:
    """Construct the right-click menu and return ``(menu, status_item)``.

    The status item is returned separately so the caller can attach a
    ``GLib.timeout_add`` callback to update its label on state changes.

    Args:
        config: the :class:`Config` (drives the "Open …" label).
        indicator_ref: the AppIndicator3 indicator (unused here, kept for
            future extensions where menu items might depend on the
            indicator's state).
        on_start: callback for the Start menu item.
        on_stop: callback for the Stop menu item.
        on_restart: callback for the Restart menu item.
        on_open: callback for the Open menu item.
        on_quit: callback for the Quit menu item.

    Returns:
        A ``(menu, status_item)`` tuple. ``status_item`` is a
        ``Gtk.MenuItem`` whose label is updated by the caller.
    """
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    menu = Gtk.Menu()
    status = Gtk.MenuItem(label="Status: …")
    status.set_sensitive(False)
    menu.append(status)

    open_item = Gtk.MenuItem(label=f"Open {config.title} ({config.url})")
    open_item.connect("activate", lambda *_: on_open())
    menu.append(open_item)

    menu.append(Gtk.SeparatorMenuItem())

    start_item = Gtk.MenuItem(label="Start")
    start_item.connect("activate", lambda *_: on_start())
    menu.append(start_item)

    stop_item = Gtk.MenuItem(label="Stop")
    stop_item.connect("activate", lambda *_: on_stop())
    menu.append(stop_item)

    restart_item = Gtk.MenuItem(label="Restart")
    restart_item.connect("activate", lambda *_: on_restart())
    menu.append(restart_item)

    menu.append(Gtk.SeparatorMenuItem())

    quit_item = Gtk.MenuItem(label="Quit Indicator")
    quit_item.connect("activate", lambda *_: on_quit())
    menu.append(quit_item)

    menu.show_all()
    return menu, status
