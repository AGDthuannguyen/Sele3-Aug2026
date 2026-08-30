"""Configuration management for Pylenium framework.

Singleton pattern ensures a single centralized configuration source.
Config priority (high to low):
    1. CLI arguments (pytest --browser firefox)
    2. Environment variables (PYLENIUM_BROWSER=firefox)
    3. User config file (config/staging.yaml)
    4. Default config (pylenium/config/default_config.yaml)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class Config:
    """Singleton configuration manager for the Pylenium framework.

    Loads and merges configuration from multiple sources with a defined
    priority order, providing a single access point for all settings.
    """

    _instance: Config | None = None
    _initialized: bool = False

    def __new__(cls) -> Config:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if Config._initialized:
            return
        self._data: dict[str, Any] = {}
        self._load_defaults()
        self._load_env_vars()
        Config._initialized = True

    def _load_defaults(self) -> None:
        """Load default configuration from default_config.yaml."""
        default_path = Path(__file__).parent / "default_config.yaml"
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}

    def _load_env_vars(self) -> None:
        """Override config with PYLENIUM_ prefixed environment variables."""
        env_mapping = {
            "PYLENIUM_BROWSER": ("browser", "type"),
            "PYLENIUM_HEADLESS": ("browser", "headless"),
            "PYLENIUM_BASE_URL": ("browser", "base_url"),
            "PYLENIUM_TIMEOUT": ("waits", "timeout"),
            "PYLENIUM_ASSERTION_TIMEOUT": ("assertions", "timeout"),
        }
        for env_var, key_path in env_mapping.items():
            value = os.environ.get(env_var)
            if value is not None:
                self._set_nested(key_path, self._parse_value(value))

    def load_file(self, filepath: str | Path) -> None:
        """Load and merge a user config file (overrides defaults).

        Args:
            filepath: Path to a YAML configuration file.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        self._deep_merge(self._data, user_config)

    def merge(self, overrides: dict[str, Any]) -> None:
        """Merge CLI or programmatic overrides into config.

        Args:
            overrides: Dictionary of configuration overrides.
        """
        self._deep_merge(self._data, overrides)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value using dot notation.

        Args:
            key: Dot-separated key path (e.g., 'browser.type').
            default: Value to return if key is not found.

        Returns:
            The configuration value, or default if not found.
        """
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a config value using dot notation.

        Args:
            key: Dot-separated key path (e.g., 'browser.type').
            value: The value to set.
        """
        keys = key.split(".")
        self._set_nested(tuple(keys), value)

    # -- Convenience properties --

    @property
    def browser_type(self) -> str:
        return self.get("browser.type", "chrome")

    @property
    def headless(self) -> bool:
        return self.get("browser.headless", False)

    @property
    def window_size(self) -> str:
        return self.get("browser.window_size", "1920x1080")

    @property
    def base_url(self) -> str:
        return self.get("browser.base_url", "")

    @property
    def page_load_timeout(self) -> int:
        return self.get("browser.page_load_timeout", 30)

    @property
    def timeout(self) -> float:
        return float(self.get("waits.timeout", 10))

    @property
    def polling_interval(self) -> float:
        return float(self.get("waits.polling_interval", 0.5))

    @property
    def assertion_timeout(self) -> float:
        return float(self.get("assertions.timeout", 5))

    @property
    def assertion_polling(self) -> float:
        return float(self.get("assertions.polling_interval", 0.25))

    @property
    def screenshot_on_failure(self) -> bool:
        return self.get("reporting.screenshot_on_failure", True)

    @property
    def reporter_type(self) -> str:
        return self.get("reporting.reporter", "allure")

    # -- Private helpers --

    def _set_nested(self, keys: tuple[str, ...], value: Any) -> None:
        """Set a value in a nested dict structure."""
        current = self._data
        for key in keys[:-1]:
            current = current.setdefault(key, {})
        current[keys[-1]] = value

    @staticmethod
    def _parse_value(value: str) -> Any:
        """Parse string values from env vars into appropriate types."""
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Recursively merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        cls._instance = None
        cls._initialized = False
