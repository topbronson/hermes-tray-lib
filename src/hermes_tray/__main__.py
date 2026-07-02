"""Run hermes-tray-lib as a module for quick smoke tests.

Usage::

    python -m hermes_tray

This is a no-op debug entry point — it prints the version and exits. Real
indicators import :func:`hermes_tray.main` from their own ``__main__.py``.
"""

from __future__ import annotations

import sys

from hermes_tray import __version__


def main() -> int:
    print(f"hermes-tray-lib {__version__}")
    print("This is a library, not a standalone indicator.")
    print("Import hermes_tray.main(cfg, probe) from your tray's __main__.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
