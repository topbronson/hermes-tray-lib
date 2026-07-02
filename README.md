# hermes-tray-lib

> Shared infrastructure for the family of Hermes-* tray indicators
> (`hermes-dashboard-tray`, `hermes-mnemosyne-tray`, `hermes-router-tray`).

A small, focused Python library that handles the boilerplate every Linux
GNOME tray indicator needs: AppIndicator3 setup, a state machine, icon
swapping with status dots, a watcher thread, and a right-click menu.
Specific indicators (the dashboard, the Mnemosyne dashboard, the Hermes
router) are thin wrappers around this library.

## Install

```bash
pip install "hermes-tray-lib @ git+https://github.com/topbronson/hermes-tray-lib"
```

## Usage

```python
from pathlib import Path

from hermes_tray import (
    Config,
    LivenessProbe,
    PortListeningProbe,
    main,
)


class MyProbe(LivenessProbe):
    def alive(self) -> bool:
        # your check
        ...


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

main(cfg, MyProbe())  # enters Gtk.main(); Ctrl-C quits
```

## API

| Symbol | Description |
|---|---|
| `Config` | Immutable, env-driven configuration (frozen dataclass). |
| `State` | Enum: `RUNNING`, `STARTING`, `STOPPED`, `RESTARTING`, `ERROR`. |
| `LivenessProbe` | Abstract base class for liveness checks. |
| `PortListeningProbe` | Probe that succeeds on TCP connect. |
| `ProcessCommandProbe` | Probe that succeeds when `ps` output contains a needle. |
| `UrlHealthProbe` | Probe that succeeds on HTTP 2xx. |
| `Indicator` | State holder + icon-swap coordinator (thread-safe). |
| `main(cfg, probe)` | Top-level entry point; builds indicator, menu, watcher, enters `Gtk.main()`. |

## Env vars

For an indicator with `name="thing"`, all settings can be overridden by env vars:

- `HERMES_THING_HOST`
- `HERMES_THING_PORT`
- `HERMES_THING_URL`
- `HERMES_THING_CWD`
- `HERMES_THING_RESTART_DELAY`
- `HERMES_THING_AUTO_START` (1/0)
- `HERMES_THING_BROWSER_CMD`

## Development

```bash
git clone https://github.com/topbronson/hermes-tray-lib
cd hermes-tray-lib
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -v
.venv/bin/ruff check src tests
.venv/bin/ruff format src tests
.venv/bin/mypy src tests
```

Pre-commit chain (ruff + mypy + gitleaks) is configured in
`.pre-commit-config.yaml`. Install with:

```bash
.venv/bin/pre-commit install
```

## License

MIT — see [LICENSE](LICENSE).
