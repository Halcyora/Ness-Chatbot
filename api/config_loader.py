"""
Configuration loader for site-specific settings.

Loads site config from config/sites/{site_id}.json and validates required fields.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


def get_config_path(site_id: str) -> Path:
    """Get the path to a site config file.
    
    Looks in config/sites/ directory relative to project root.
    """
    # Navigate up from api/ to project root, then down to config/sites/
    project_root = Path(__file__).parent.parent
    return project_root / "config" / "sites" / f"{site_id}.json"


def load_site_config(site_id: str) -> Dict[str, Any]:
    """
    Load and validate site configuration.

    Args:
        site_id: The site identifier (e.g., 'ness')

    Returns:
        Parsed site configuration dictionary

    Raises:
        ConfigError: If the config file is missing or invalid
        ValueError: If required keys are missing from the config
    """
    config_path = get_config_path(site_id)

    # Check if config file exists
    if not config_path.exists():
        raise ConfigError(
            f"Site config not found: {config_path}\n"
            f"Expected config file at: {config_path}"
        )

    # Load JSON
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {config_path}: {e}")
    except IOError as e:
        raise ConfigError(f"Failed to read {config_path}: {e}")

    # Validate required top-level keys
    required_keys = [
        "site_id",
        "base_url",
        "sitemap_seeds",
        "dynamic_pages",
        "greeting_keywords",
        "branding",
        "welcome_message",
        "quick_actions",
    ]

    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValueError(
            f"Missing required keys in {site_id} config: {', '.join(missing_keys)}"
        )

    # Validate site_id matches filename
    if config["site_id"] != site_id:
        raise ValueError(
            f"Site ID mismatch: config['site_id'] = '{config['site_id']}' "
            f"but file is for '{site_id}'"
        )

    # Validate branding has required sub-keys
    branding_keys = ["name", "primary_color", "logo_url"]
    missing_branding = [key for key in branding_keys if key not in config["branding"]]
    if missing_branding:
        raise ValueError(
            f"Missing branding keys in {site_id} config: {', '.join(missing_branding)}"
        )

    # Validate quick_actions
    if not isinstance(config["quick_actions"], list) or not config["quick_actions"]:
        raise ValueError(f"quick_actions must be a non-empty list in {site_id} config")

    for i, action in enumerate(config["quick_actions"]):
        if "label" not in action or "route" not in action:
            raise ValueError(
                f"quick_actions[{i}] missing 'label' or 'route' in {site_id} config"
            )
        if action["route"] not in ["rag", "tool", "canned"]:
            raise ValueError(
                f"quick_actions[{i}]['route'] must be 'rag', 'tool', or 'canned', "
                f"got '{action['route']}' in {site_id} config"
            )

    return config


def get_site_config_or_exit(site_id: str) -> Dict[str, Any]:
    """
    Load site config, exit with error message if it fails.

    Useful for CLI/app initialization where you want to fail fast.
    """
    try:
        return load_site_config(site_id)
    except (ConfigError, ValueError) as e:
        print(f"Configuration Error: {e}", file=__import__("sys").stderr)
        __import__("sys").exit(1)
