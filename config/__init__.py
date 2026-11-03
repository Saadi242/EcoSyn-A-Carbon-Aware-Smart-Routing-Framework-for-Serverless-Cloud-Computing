"""Configuration loader and manager for the EcoSyn framework."""

import os
from pathlib import Path
from typing import Any, Dict
import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def load_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Loads and parses the YAML configuration file.

    Args:
        config_path: Optional path to the configuration file.
                     Defaults to config/config.yaml.

    Returns:
        Dict[str, Any]: Parsed configuration dictionary.
    """
    if config_path is None:
        target_path = DEFAULT_CONFIG_PATH
    else:
        target_path = Path(config_path)

    if not target_path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {target_path}")

    with open(target_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


__all__ = ["load_config", "DEFAULT_CONFIG_PATH"]
