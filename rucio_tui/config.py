"""
config.py — Configuration loading, merging, and alias validation.
"""
from __future__ import annotations

import json
import os
import pathlib

def load_config() -> dict:
    """
    Load system-wide and user configuration files, merging them together.
    User config overrides system config for duplicate keys.
    """
    system_config_path = os.environ.get("RUCIO_TUI_SYSTEM_CONFIG", "/etc/rucio-tui.json")
    user_config_path = os.environ.get("RUCIO_TUI_USER_CONFIG", "~/.rucio-tui.json")

    config = {"aliases": {}, "_loaded_files": []}

    # Load system configuration
    sys_path = pathlib.Path(system_config_path)
    sys_exists = sys_path.exists() and sys_path.is_file()
    config["_loaded_files"].append((str(sys_path), sys_exists))

    if sys_exists:
        try:
            with open(sys_path, "r", encoding="utf-8") as f:
                sys_config = json.load(f)
                if isinstance(sys_config, dict):
                    # Merge system aliases
                    sys_aliases = sys_config.get("aliases", {})
                    if isinstance(sys_aliases, dict):
                        config["aliases"].update(sys_aliases)
                    
                    # Merge other configuration fields for future flexibility
                    for k, v in sys_config.items():
                        if k not in ("aliases", "_loaded_files"):
                            config[k] = v
        except Exception:
            pass

    # Load user configuration
    user_expanded = os.environ.get("RUCIO_TUI_USER_CONFIG", user_config_path)
    if user_expanded.startswith("~"):
        user_expanded = os.path.expanduser(user_expanded)
    user_path = pathlib.Path(user_expanded)
    user_exists = user_path.exists() and user_path.is_file()
    config["_loaded_files"].append((str(user_path), user_exists))

    if user_exists:
        try:
            with open(user_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                if isinstance(user_config, dict):
                    # Merge user aliases, overriding system aliases
                    user_aliases = user_config.get("aliases", {})
                    if isinstance(user_aliases, dict):
                        config["aliases"].update(user_aliases)

                    # Merge other configuration fields, overriding system config
                    for k, v in user_config.items():
                        if k not in ("aliases", "_loaded_files"):
                            config[k] = v
        except Exception:
            pass

    return config


def validate_aliases(config: dict) -> dict[str, str | None]:
    """
    Validate all defined aliases in the configuration against the click command tree.
    Returns a dictionary mapping each alias to its validation error string,
    or None if the alias is valid.
    """
    from rucio_tui.command_parser import parse_help

    results = {}
    aliases = config.get("aliases", {})
    if not isinstance(aliases, dict):
        return results

    for alias, target in aliases.items():
        if not target:
            results[alias] = "Target is empty"
            continue

        if isinstance(target, str):
            target_list = target.split()
        elif isinstance(target, list):
            target_list = target
        else:
            results[alias] = "Target must be a string or a list of strings"
            continue

        if not all(isinstance(x, str) for x in target_list):
            results[alias] = "Target elements must be strings"
            continue

        try:
            # Reconstruct the command path (prefixing "rucio" which is skipped by parse_help)
            path = ["rucio"] + target_list
            parse_help(path)
            results[alias] = None  # Valid command path
        except Exception as e:
            results[alias] = str(e)

    return results
