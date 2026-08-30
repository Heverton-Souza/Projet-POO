from dataclasses import dataclass, field
from typing import Any


@dataclass
class Combat:
    id: str
    character_id: str
    enemy_id: str
    enemy_name: str
    status: str
    enemy_health: int
    enemy_max_health: int
    started_at: str
    finished_at: str | None = None
    turns: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "characterId": self.character_id,
            "enemyId": self.enemy_id,
            "enemyName": self.enemy_name,
            "status": self.status,
            "enemyHealth": self.enemy_health,
            "enemyMaxHealth": self.enemy_max_health,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "turns": self.turns,
        }
