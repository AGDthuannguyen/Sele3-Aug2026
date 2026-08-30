"""Configuration management for Pylenium framework using Dynaconf.

Dynaconf handles all config sources automatically:
    - Default settings from default_config.yaml
    - User config files (e.g., config/staging.yaml)
    - Environment variables prefixed with PYLENIUM_
    - CLI arguments (injected via pytest plugin in Phase 4)

All environment variables use the prefix PYLENIUM_.
Example: PYLENIUM_BROWSER__TYPE=firefox (double underscore for nested keys)
"""

from pathlib import Path

from dynaconf import Dynaconf

# Path to the default configuration file shipped with the framework
_DEFAULT_CONFIG = Path(__file__).parent / "default_config.yaml"

settings = Dynaconf(
    envvar_prefix="PYLENIUM",
    settings_files=[str(_DEFAULT_CONFIG)],
    environments=False,
    merge_enabled=True,
    load_dotenv=True,
)
