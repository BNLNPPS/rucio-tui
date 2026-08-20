"""
command_parser.py — Builds a CommandNode tree by introspecting the rucio Click
command group directly, rather than spawning subprocesses.

Direct Click API introspection is ~200x faster than running `rucio --help` in a
subprocess (0.017 s for the full tree vs ~3.5 s for 15 sequential subprocesses).
"""
from __future__ import annotations

import click
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class OptionDef:
    flags: list[str]
    metavar: str
    help: str
    required: bool = False
    default: str | None = None
    choices: list[str] | None = None   # set for click.Choice parameters
    is_flag: bool = False              # True for boolean flag options (no value argument)


@dataclass
class ArgumentDef:
    name: str
    metavar: str
    required: bool = True


@dataclass
class CommandNode:
    name: str
    description: str
    path: list[str]          # e.g. ["rucio", "did", "add"]
    is_group: bool = False
    children: list["CommandNode"] = field(default_factory=list)
    options: list[OptionDef] = field(default_factory=list)
    arguments: list[ArgumentDef] = field(default_factory=list)
    help_text: str = ""      # kept for interface compatibility


# ---------------------------------------------------------------------------
# Click → CommandNode conversion
# ---------------------------------------------------------------------------

def _build_node(cmd: click.BaseCommand, path: list[str]) -> CommandNode:
    """Recursively convert a Click command/group into a CommandNode tree."""
    ctx = click.Context(cmd, info_name=path[-1])
    name = path[-1]
    description = (cmd.help or "").strip()
    is_group = isinstance(cmd, click.MultiCommand)

    options: list[OptionDef] = []
    arguments: list[ArgumentDef] = []
    children: list[CommandNode] = []

    for param in cmd.params:
        # Skip the --help flag (eager, non-value-exposing option)
        if (
            isinstance(param, click.Option)
            and getattr(param, "is_eager", False)
            and not getattr(param, "expose_value", True)
        ):
            continue

        if isinstance(param, click.Argument):
            arguments.append(ArgumentDef(
                name=param.name.upper().replace("-", "_"),
                metavar=param.make_metavar(ctx).strip("<>[]"),
                required=param.required,
            ))

        elif isinstance(param, click.Option):
            flags = list(param.opts)
            is_flag = bool(getattr(param, "is_flag", False))
            choices: list[str] | None = None
            if isinstance(param.type, click.Choice):
                choices = list(param.type.choices)
                metavar = "|".join(choices)
            else:
                metavar = (param.type.name or "TEXT").upper()

            raw = param.default
            default_str: str | None = None
            if raw is not None and not isinstance(raw, bool):
                try:
                    default_str = str(raw)
                except Exception:
                    pass

            options.append(OptionDef(
                flags=flags,
                metavar=metavar,
                help=param.help or "",
                required=param.required,
                default=default_str,
                choices=choices,
                is_flag=is_flag,
            ))

    if is_group:
        for child_name in cmd.list_commands(ctx):
            child_cmd = cmd.get_command(ctx, child_name)
            if child_cmd is not None:
                children.append(_build_node(child_cmd, path + [child_name]))

    return CommandNode(
        name=name,
        description=description,
        path=path,
        is_group=is_group,
        children=children,
        options=options,
        arguments=arguments,
    )


# ---------------------------------------------------------------------------
# Root command provider — swappable for testing
# ---------------------------------------------------------------------------

def _get_root_click_command() -> click.BaseCommand:
    """Return the root Click command for rucio. Override in tests."""
    from rucio.cli.command import main  # type: ignore[import]
    return main


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_root_cache: CommandNode | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_root() -> CommandNode:
    """
    Return the root CommandNode for rucio with the full tree pre-built.
    Cached after the first call (~0.02 s).
    """
    global _root_cache
    if _root_cache is None:
        _root_cache = _build_node(_get_root_click_command(), ["rucio"])
    return _root_cache


def parse_help(path: list[str]) -> CommandNode:
    """
    Return the CommandNode for the given path (e.g. ["rucio", "did", "add"]).
    Builds the full tree on first call, then navigates the in-memory tree.
    """
    node = build_root()
    for part in path[1:]:   # skip "rucio"
        match = next((c for c in node.children if c.name == part), None)
        if match is None:
            raise ValueError(f"Command not found: {path!r}")
        node = match
    return node


def get_children(node: CommandNode) -> list[CommandNode]:
    """Return the children of a group node (already resolved in the tree)."""
    return node.children if node.is_group else []


def clear_cache() -> None:
    """Clear the cached command tree (useful in tests)."""
    global _root_cache
    _root_cache = None
