from dataclasses import dataclass
from typing import Any

from .attributes import Attributes


@dataclass
class CharacterClass:
    id: str
    name: str
    description: str
    attributes: Attributes
    base_health: int
    base_energy: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "attributes": self.attributes.to_dict(),
            "baseHealth": self.base_health,
            "baseEnergy": self.base_energy,
        }
