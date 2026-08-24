# rucio-tui

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

A modern, keyboard-driven [Textual](https://textual.textualize.io/) TUI for browsing and executing [Rucio](https://rucio.cern.ch/) CLI commands interactively.

`rucio-tui` wraps the `rucio` CLI so you can:

- **Browse** the entire command hierarchy in a keyboard-driven menu
- **Fill in** options and arguments through a dynamically generated form
- **Execute** any leaf command and watch its output stream live in the terminal — all without leaving the TUI

With no extra arguments, `rucio-tui` launches the interactive interface. With arguments, it is a transparent pass-through to `rucio`, so it can stand in for the CLI in scripts and aliases.

![rucio-tui running `rucio did content list`](Screenshot-rucio_tui.jpg)

---

## Features

| Feature | Description |
|---------|-------------|
| Command browser | Navigable tree of every `rucio` command group and sub-command |
| Auto-generated forms | Each leaf command gets an input form built from Click parameter metadata |
| Flag checkboxes | Boolean flags (e.g. `--csv`) render as checkboxes |
| Enum dropdowns | Options with a fixed set of choices render as `Select` widgets |
| Env-var expansion | Input fields expand `$VAR` / `${VAR}` before the command is built |
| Live output | Command stdout/stderr stream into a scrollable panel |
| Save to file | Optional output path (also supports env-var expansion) |
| VOMS check | Warns if the X.509 / VOMS proxy is missing or expired |
| Clickable breadcrumb | Jump back to any parent in the path (e.g. `rucio › rse › list`) |
| Pass-through mode | `rucio-tui <args>` is equivalent to `rucio <args>` |
| Aliases | Optional JSON aliases (`~/.rucio-tui.json` and `/etc/rucio-tui.json`) |

---

## Requirements

- Python ≥ 3.10 — 3.11 (default), 3.12, 3.13, and 3.14 are all supported
- Rucio ≥ 37
- [CVMFS](https://cernvm.cern.ch/fs/) with `/cvmfs/grid.cern.ch` is recommended so VOMS config and CA certificates can be copied into the venv
- A valid grid certificate / VOMS proxy to talk to a real Rucio instance

`build_env-uv.sh` will install `uv` automatically if it is not already on `PATH`.

---

## Ready-made deployments

Pre-built environments are available on CVMFS and at CERN — no build required:

| Site | Location | Activate |
|------|----------|----------|
| BNL (CVMFS) | `/cvmfs/atlas.sdcc.bnl.gov/users/yesw/rucio-tui/` | `source /cvmfs/atlas.sdcc.bnl.gov/users/yesw/rucio-tui/setupMe.sh` |
| CERN (AFS) | `~yesw/public/rucio-tui-venv/` | `source ~yesw/public/rucio-tui-venv/setupMe.sh` |

After activation, run `rucio-tui` (see [Activate and run](#activate-and-run)).

---

## Build the environment

Run the builder **directly** — do **not** source it:

```bash
./build_env-uv.sh                 # CPython 3.11 (default)
./build_env-uv.sh --python 3.12   # or 3.13, 3.14, etc.
# or
bash build_env-uv.sh -p 3.14
```

This creates a self-contained, relocatable `venv/` that includes:

- The selected CPython under `venv/python/`
- The `rucio-tui` package and its dependencies (`textual`, `rich`, `click`, `rucio`, …)
- VOMS config, certificates, and `rucio.cfg` under `venv/etc/`
- `venv/setupMe.sh` — the activation script
- `venv/buildStamp.txt` — UTC build timestamp

---

## Activate and run

```bash
source venv/setupMe.sh
rucio-tui
```

`setupMe.sh` activates the venv, exports `RUCIO_CONFIG` / VOMS-related paths, and (if `voms-proxy-init` is available) obtains a proxy when needed.

Default VO is `atlas`. Override it:

```bash
source venv/setupMe.sh --voms atlas
```

Leave the environment with `deactivate2`.

### Command-line usage

```text
rucio-tui                          # launch the interactive TUI
rucio-tui whoami                   # pass-through: rucio whoami
rucio-tui did list "opendata:*"    # pass-through with arguments
rucio-tui -h                       # this tool's help
rucio-tui --buildStamp             # print the venv build stamp
rucio-tui --list-commands          # print the full rucio command tree
rucio-tui --list-aliases           # show alias config and validity
```

You can also run `python -m rucio_tui` after the environment is active.

---

## Keyboard shortcuts

Available on every screen:

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move in the command list or form |
| `Enter` | Open a group, or run when on the last required field |
| `b` | Back |
| `h` | Home (root menu) |
| `q` | Quit |
| `Ctrl+R` | Run command (on the runner screen) |

---

## Source layout

Application code lives in [`rucio_tui/`](rucio_tui/):

```text
rucio_tui/
├── cli.py              # Entry point: TUI, pass-through, --help, --list-commands
├── app.py              # Textual App and splash screen
├── command_parser.py   # Click introspection → command tree
├── config.py           # Alias / JSON config loading
├── voms.py             # Async VOMS proxy check
├── screens/            # Menu (browse) and runner (form + live output)
├── widgets/            # Breadcrumb, command list, output panel
└── styles/             # Textual CSS
```

The command tree is built by walking the installed `rucio` Click group in-process (no `rucio --help` subprocess per command), then rendered as menus and forms.

---

## Development

After `source venv/setupMe.sh`:

```bash
# reinstall in editable mode while hacking on rucio_tui/
uv pip install -e .

pytest
```

Dev extras (`pytest`, `pytest-asyncio`, `anyio`) are declared under `[project.optional-dependencies] dev` in `pyproject.toml`.

---

## Configuration

- **Rucio client:** `venv/etc/rucio.cfg` (copied from the repo `rucio.cfg` at build time). Pointed to by `RUCIO_CONFIG` after `source venv/setupMe.sh`.
- **TUI aliases:** JSON files at `/etc/rucio-tui.json` (system) and `~/.rucio-tui.json` (user). User values override system values. Paths can be overridden with `RUCIO_TUI_SYSTEM_CONFIG` and `RUCIO_TUI_USER_CONFIG`.

Example user config:

```json
{
  "aliases": {
    "who": ["whoami"],
    "ls": ["did", "list"]
  }
}
```

---

## License

Licensed under the [Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0) — the same license as [rucio-clients](https://pypi.org/project/rucio-clients/).

See [LICENSE](LICENSE) for the full text.

Author: Shuwei Ye \<yesw@bnl.gov\>
