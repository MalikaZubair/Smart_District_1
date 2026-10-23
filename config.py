"""config.py: .env (project se bahar) se settings load karta hai."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_FILE = Path.home() / ".data_sync" / ".env"
REQUIRED_KEYS = ("CRM_API_KEY", "BILLING_API_KEY", "SUPPORT_API_KEY")


class ConfigError(Exception):
    """Config ka masla."""


@dataclass(frozen=True)
class Settings:
    crm_key: str = field(repr=False)          # repr/print mein nahi aayegi
    billing_key: str = field(repr=False)
    support_key: str = field(repr=False)
    timeout: float = 5.0
    env_file: Path = DEFAULT_ENV_FILE


def resolve_env_path() -> Path:
    # DATA_SYNC_ENV_FILE se custom path diya ja sakta hai
    path = Path(os.environ.get("DATA_SYNC_ENV_FILE", DEFAULT_ENV_FILE)).expanduser().resolve()
    if path == PROJECT_DIR or PROJECT_DIR in path.parents:
        raise ConfigError(f".env codebase ke andar hai ({path}). Usay project folder se bahar rakhein.")
    if not path.is_file():
        raise ConfigError(f".env file nahi mili: {path}")
    return path


def load_settings() -> Settings:
    path = resolve_env_path()
    values = dotenv_values(path)

    missing = [k for k in REQUIRED_KEYS if not (values.get(k) or "").strip()]
    if missing:
        raise ConfigError(f".env mein ye keys missing hain: {', '.join(missing)}")

    try:
        timeout = float(values.get("TIMEOUT_SECONDS") or 5)
    except ValueError:
        raise ConfigError("TIMEOUT_SECONDS number hona chahiye") from None
    if timeout <= 0:
        raise ConfigError("TIMEOUT_SECONDS zero se bara hona chahiye")

    return Settings(
        crm_key=values["CRM_API_KEY"].strip(),
        billing_key=values["BILLING_API_KEY"].strip(),
        support_key=values["SUPPORT_API_KEY"].strip(),
        timeout=timeout,
        env_file=path,
    )