"""
Domain for DVC/DVCLive integration.

Ref: https://docs.ultralytics.com/ru/integrations/dvc/
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class DVCConfig:
    enabled: bool

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DVCConfig":
        return cls(enabled=bool(d.get("enabled", False)))

    def to_dict(self) -> dict[str, Any]:
        return {"enabled": self.enabled}
