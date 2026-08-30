from dataclasses import dataclass
from typing import Any


@dataclass
class Mission:
    id: str
    title: str
    description: str
    objective: str
    min_level: int
    status: str
    target: int
    reward_experience: int
    reward_coins: int
    reward_item_id: str | None
    reward_item_quantity: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "objective": self.objective,
            "minLevel": self.min_level,
            "status": self.status,
            "target": self.target,
            "rewardExperience": self.reward_experience,
            "rewardCoins": self.reward_coins,
            "rewardItemId": self.reward_item_id,
            "rewardItemQuantity": self.reward_item_quantity,
        }
