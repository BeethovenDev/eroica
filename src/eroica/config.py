"""Configuration model, tiers and persistence.

Configuration is stored as JSON at :func:`eroica.paths.config_home` so that the
package stays dependency-free and readable on every supported Python version.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import IntEnum
from pathlib import Path

from eroica import log
from eroica.errors import ConfigError
from eroica.paths import config_home

_log = log.get_logger("config")

__all__ = [
    "DOH_PROVIDERS",
    "Config",
    "Tier",
    "config_path",
    "load_config",
    "save_config",
]


class Tier(IntEnum):
    """How aggressive hardening should be.

    Tiers are ordered: a higher tier is a strict superset of the lower ones.
    This lets every setting declare the *minimum* tier at which it applies.
    """

    STANDARD = 1
    STRICT = 2
    PARANOID = 3

    @classmethod
    def coerce(cls, value: Tier | int | str) -> Tier:
        """Best-effort conversion from a CLI string, int or enum."""
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            try:
                return cls(value)
            except ValueError as exc:
                raise ConfigError(f"unknown tier {value!r}") from exc
        try:
            return cls[str(value).strip().upper()]
        except KeyError as exc:
            names = ", ".join(t.name.lower() for t in cls)
            raise ConfigError(f"unknown tier {value!r}; choose one of: {names}") from exc

    def describe(self) -> str:
        return {
            Tier.STANDARD: "sane, low-friction hardening that rarely breaks sites",
            Tier.STRICT: "aggressive hardening; some sites may need exceptions",
            Tier.PARANOID: "maximum hardening; expect breakage and manual tuning",
        }[self]


#: Curated DNS-over-HTTPS resolvers. ``None`` means "leave the browser default".
DOH_PROVIDERS: dict[str, str | None] = {
    "mullvad": "https://dns.mullvad.net/dns-query",
    "quad9": "https://dns.quad9.net/dns-query",
    "cloudflare": "https://cloudflare-dns.com/dns-query",
    "google": "https://dns.google/dns-query",
    "system": None,
}


@dataclass
class Config:
    """User configuration with conservative defaults."""

    default_tier: Tier = Tier.STRICT
    doh_provider: str = "mullvad"
    ua_mode: str = "consistent"
    backup_user_js: bool = True

    def __post_init__(self) -> None:
        self.default_tier = Tier.coerce(self.default_tier)
        if self.doh_provider not in DOH_PROVIDERS:
            valid = ", ".join(sorted(DOH_PROVIDERS))
            raise ConfigError(f"unknown DoH provider {self.doh_provider!r}; choose one of: {valid}")
        if self.ua_mode not in {"consistent", "off"}:
            raise ConfigError("ua_mode must be 'consistent' or 'off'")

    @property
    def doh_uri(self) -> str | None:
        """The DoH template URL, or ``None`` to leave the default in place."""
        return DOH_PROVIDERS[self.doh_provider]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["default_tier"] = self.default_tier.name.lower()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Config:
        known = {f: data[f] for f in cls.__dataclass_fields__ if f in data}
        return cls(**known)  # type: ignore[arg-type]


def config_path() -> Path:
    """Return the location of the configuration file."""
    return config_home() / "config.json"


def load_config() -> Config:
    """Load configuration from disk, returning defaults when absent."""
    path = config_path()
    if not path.is_file():
        return Config()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"could not read {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a JSON object")
    return Config.from_dict(raw)


def save_config(config: Config) -> Path:
    """Persist configuration, creating parent directories as needed."""
    path = config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(config.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise ConfigError(f"could not write {path}: {exc}") from exc
    _log.debug("wrote config to %s", path)
    return path
