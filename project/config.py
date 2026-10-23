import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from exceptions import ConfigError

BASE_DIR = Path(__file__).resolve().parent


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Missing environment variable: {name}")
    return value


def _number(name: str, cast=int):
    try:
        return cast(_require(name))
    except ValueError:
        raise ConfigError(f"{name} must be a valid {cast.__name__}") from None


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    report_dir: Path
    log_dir: Path
    pass_marks: float
    fine_per_day: int
    grace_days: int
    max_fine: int
    admin_password: str


def load_settings() -> Settings:
    load_dotenv(BASE_DIR / ".env")
    return Settings(
        data_dir=BASE_DIR / _require("DATA_DIR"),
        report_dir=BASE_DIR / _require("REPORT_DIR"),
        log_dir=BASE_DIR / _require("LOG_DIR"),
        pass_marks=_number("PASS_MARKS", float),
        fine_per_day=_number("FINE_PER_DAY"),
        grace_days=_number("GRACE_DAYS"),
        max_fine=_number("MAX_FINE"),
        admin_password=_require("ADMIN_PASSWORD"),
    )


settings = load_settings()