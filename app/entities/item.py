from dataclasses import dataclass
from typing import Any


@dataclass
class Item:
    id: str
    name: str
    type: str
    description: str
    rarity: str
    value: int
    effect_health: int
    effect_energy: int
    attack_bonus: int
    defense_bonus: int
    required_class_id: str | None
    min_level: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "rarity": self.rarity,
            "value": self.value,
            "effectHealth": self.effect_health,
            "effectEnergy": self.effect_energy,
            "attackBonus": self.attack_bonus,
            "defenseBonus": self.defense_bonus,
            "requiredClassId": self.required_class_id,
            "minLevel": self.min_level,
        }
