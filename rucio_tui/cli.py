"""
cli.py — Entry point: pass-through to `rucio` or launch the TUI.

Author: Shuwei Ye <yesw@bnl.gov>
"""
from __future__ import annotations

import os
import pathlib
import sys

__author__ = "Shuwei Ye <yesw@bnl.gov>"

HELP_TEXT = """\
Usage: rucio-tui [OPTIONS] [RUCIO_ARGS]...

  rucio-tui — Interactive Textual TUI for exploring and running rucio commands.

  With no arguments, launches the interactive TUI.
  With arguments, passes them straight through to the rucio CLI.

Options:
  -h, --help        Show this message and exit.
  --buildStamp      Print the build stamp of this installation and exit.
  --list-commands   Print the full list of all available rucio commands in tree style.
  --list-aliases    List the defined aliases and configuration file status, and exit.

Examples:
  rucio-tui                          Launch the interactive TUI
  rucio-tui whoami                   Run: rucio whoami
  rucio-tui did list "opendata:*"    Run: rucio did list "opendata:*"

Author: Shuwei Ye <yesw@bnl.gov>
"""


def _find_build_stamp() -> str | None:
    """
    Return the content of buildStamp.txt, or None if not found.

    The file is expected at the venv root (one level above the ``bin/``
    directory that contains the Python executable), matching the layout
    created by build_env-uv.sh:

        <venv>/
          bin/python   ← sys.executable
          buildStamp.txt
    """
    stamp_file = pathlib.Path(sys.executable).parent.parent / "buildStamp.txt"
    if stamp_file.exists():
        return stamp_file.read_text().strip()
    return None


def _print_tree() -> None:
    """Print the command tree for all available rucio commands."""
    from rucio_tui.command_parser import build_root, CommandNode

    def print_node(node: CommandNode, level: int = 0) -> None:
        if node.name != "rucio":
            indent = "  " * (level - 1)
            name_disp = node.name + ("/" if node.is_group else "")
            desc = node.description.split("\n")[0] if node.description else ""
            print(f"{indent}- {name_disp}: {desc}")

        # Recurse into children
        for child in node.children:
            print_node(child, level + 1 if node.name != "rucio" else level)

    print_node(build_root())


def main() -> None:
    """
    If arguments are provided, check for alias expansion, then
    pass them straight through to `rucio`.
    If --help / -h is given, print rucio-tui's own usage and exit.
    If --buildStamp is given, print the build stamp and exit.
    If --list-commands is given, print the command tree and exit.
    If --list-aliases is given, list all defined aliases and exit.
    Otherwise, launch the Textual TUI.
    """
    from rucio_tui.config import load_config, validate_aliases

    config = load_config()
    aliases = config.get("aliases", {})

    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help"):
        print(HELP_TEXT, end="")
        sys.exit(0)

    if args and args[0] == "--list-aliases":
        results = validate_aliases(config)
        loaded_files = config.get("_loaded_files", [])

        print("Configuration files:")
        for path, found in loaded_files:
            status = "FOUND" if found else "NOT FOUND"
            print(f"  {path} ({status})")
        print()

        print("Active Aliases:")
        if not aliases:
            print("  No aliases defined.")
            sys.exit(0)

        has_errors = False
        for alias, error in results.items():
            target = aliases[alias]
            target_str = " ".join(target) if isinstance(target, list) else target
            if error:
                print(f"  {alias} -> {target_str}: INVALID ({error})")
                has_errors = True
            else:
                print(f"  {alias} -> {target_str}: VALID")
        sys.exit(1 if has_errors else 0)

    if args and args[0] == "--buildStamp":
        stamp = _find_build_stamp()
        if stamp:
            print(stamp)
        else:
            print(
                "Error: buildStamp.txt not found "
                f"(looked in {pathlib.Path(sys.executable).parent.parent})",
                file=sys.stderr,
            )
            sys.exit(1)
        sys.exit(0)

    if args and args[0] == "--list-commands":
        _print_tree()
        sys.exit(0)

    if args:
        # Expand alias if the first argument matches
        if args[0] in aliases:
            target = aliases[args[0]]
            if isinstance(target, str):
                target_list = target.split()
            else:
                target_list = target
            args = target_list + args[1:]

        # Replace this process with `rucio <args…>` — identical behaviour.
        top_dir = os.environ.get("TopDir", "").rstrip("/")
        candidate = f"{top_dir}/rucio" if top_dir else ""
        if candidate and os.path.exists(candidate):
            rucio_cmd = candidate
        else:
            rucio_cmd = "rucio"
        os.execvp(rucio_cmd, ["rucio"] + args)
    else:
        from rucio_tui.app import RucioTuiApp
        app = RucioTuiApp()
        app.run()
