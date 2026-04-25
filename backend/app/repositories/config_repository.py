"""
Config Repository — System configuration and settings access.

Provides centralized access to:
- Nudge engine configuration
- Rate limits and thresholds
- Admin settings
"""

from uuid import UUID
from typing import List, Any

from sqlalchemy.orm import Session

from app.models.lookup.nudge_config import NudgeConfig


class ConfigRepository:
    """Centralized access to system configuration."""

    def __init__(self, db: Session):
        self.db = db

    # ---- NudgeConfig ----

    def get_config(self, key: str) -> str | None:
        """
        Get a configuration value by key.

        Args:
            key: Configuration key (e.g., "nudge_max_daily_count")

        Returns:
            Configuration value or None if not found.
        """
        config = (
            self.db.query(NudgeConfig).filter(NudgeConfig.key == key).first()
        )
        return config.value if config else None

    def get_config_typed(self, key: str, type_fn=str) -> Any | None:
        """
        Get a configuration value and convert to type.

        Args:
            key: Configuration key
            type_fn: Type conversion function (int, float, bool, etc.)

        Returns:
            Converted value or None.
        """
        value = self.get_config(key)
        if value is None:
            return None
        try:
            return type_fn(value)
        except (ValueError, TypeError):
            return None

    def get_int_config(self, key: str, default: int = 0) -> int:
        """Get integer config value with default."""
        value = self.get_config_typed(key, int)
        return value if value is not None else default

    def get_float_config(self, key: str, default: float = 0.0) -> float:
        """Get float config value with default."""
        value = self.get_config_typed(key, float)
        return value if value is not None else default

    def get_bool_config(self, key: str, default: bool = False) -> bool:
        """Get boolean config value with default."""
        value = self.get_config(key)
        if value is None:
            return default
        return value.lower() in ["true", "yes", "1"]

    def set_config(self, key: str, value: str) -> NudgeConfig:
        """
        Set or update a configuration value.

        Args:
            key: Configuration key
            value: Configuration value (stored as string)

        Returns:
            Updated NudgeConfig object.
        """
        config = (
            self.db.query(NudgeConfig).filter(NudgeConfig.key == key).first()
        )

        if config:
            config.value = value
            self.db.merge(config)
        else:
            config = NudgeConfig(key=key, value=value)
            self.db.add(config)

        self.db.flush()
        return config

    def find_all_configs(self) -> List[NudgeConfig]:
        """Fetch all configuration settings."""
        return self.db.query(NudgeConfig).all()

    def config_exists(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return (
            self.db.query(NudgeConfig).filter(NudgeConfig.key == key).first()
            is not None
        )

    def delete_config(self, key: str) -> bool:
        """Delete a configuration setting. Returns True if found and deleted."""
        config = (
            self.db.query(NudgeConfig).filter(NudgeConfig.key == key).first()
        )
        if config:
            self.db.delete(config)
            self.db.flush()
            return True
        return False

    # ---- Batch Operations ----

    def bulk_set_configs(self, configs: dict[str, str]) -> List[NudgeConfig]:
        """
        Set multiple configuration values at once.

        Args:
            configs: Dictionary of key -> value pairs

        Returns:
            List of updated NudgeConfig objects.
        """
        results = []
        for key, value in configs.items():
            results.append(self.set_config(key, value))
        return results

    def find_configs_by_prefix(self, prefix: str) -> List[NudgeConfig]:
        """Find all configs whose keys start with a prefix."""
        return (
            self.db.query(NudgeConfig)
            .filter(NudgeConfig.key.like(f"{prefix}%"))
            .all()
        )
