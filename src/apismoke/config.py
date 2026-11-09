"""Load and validate a JSON check file."""
from __future__ import annotations

import json
import os
import re
from typing import Any

_ENV = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


class ConfigError(Exception):
    """The check file is missing, malformed or references an unset variable."""


def expand_env(value: Any) -> Any:
    """Replace ``${VAR}`` in every string of a nested structure."""
    if isinstance(value, str):
        def sub(match):
            name = match.group(1)
            if name not in os.environ:
                raise ConfigError(f"environment variable {name} is not set")
            return os.environ[name]
        return _ENV.sub(sub, value)
    if isinstance(value, list):
        return [expand_env(v) for v in value]
    if isinstance(value, dict):
        return {k: expand_env(v) for k, v in value.items()}
    return value


def load_config(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc.strerror}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} is not valid JSON: {exc}") from exc
    return validate(expand_env(raw))


def validate(config: Any) -> dict:
    if not isinstance(config, dict):
        raise ConfigError("top level must be a JSON object")
    base_url = config.get("base_url", "")
    if not isinstance(base_url, str):
        raise ConfigError("base_url must be a string")
    checks = config.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ConfigError("'checks' must be a non-empty list")
    names = set()
    for i, check in enumerate(checks, 1):
        where = f"check #{i}"
        if not isinstance(check, dict):
            raise ConfigError(f"{where} must be an object")
        name = check.get("name")
        if not name or not isinstance(name, str):
            raise ConfigError(f"{where} needs a 'name'")
        if name in names:
            raise ConfigError(f"duplicate check name '{name}'")
        names.add(name)
        if not isinstance(check.get("path"), str):
            raise ConfigError(f"check '{name}' needs a 'path'")
        method = str(check.get("method", "GET")).upper()
        if method not in _METHODS:
            raise ConfigError(f"check '{name}' has unsupported method {method}")
        check["method"] = method
        check.setdefault("expect", {"status": 200})
    return config
