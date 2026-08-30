from dataclasses import dataclass
from typing import Any

from .attributes import Attributes


@dataclass
class Race:
    id: str
    name: str
    description: str
    modifiers: Attributes

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "modifiers": self.modifiers.to_dict(),
        }
