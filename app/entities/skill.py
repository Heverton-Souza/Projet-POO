from dataclasses import dataclass
from typing import Any


@dataclass
class Skill:
    id: str
    name: str
    description: str
    type: str
    energy_cost: int
    damage: int
    effect: str
    cooldown: int
    min_level: int
    class_id: str | None = None
    race_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "energyCost": self.energy_cost,
            "damage": self.damage,
            "effect": self.effect,
            "cooldown": self.cooldown,
            "minLevel": self.min_level,
            "classId": self.class_id,
            "raceId": self.race_id,
        }
