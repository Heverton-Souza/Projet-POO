from dataclasses import dataclass
from typing import Any


@dataclass
class Enemy:
    id: str
    name: str
    type: str
    level: int
    health: int
    strength: int
    defense: int
    agility: int
    reward_experience: int
    reward_coins: int
    reward_item_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "level": self.level,
            "health": self.health,
            "strength": self.strength,
            "defense": self.defense,
            "agility": self.agility,
            "rewardExperience": self.reward_experience,
            "rewardCoins": self.reward_coins,
            "rewardItemId": self.reward_item_id,
        }
