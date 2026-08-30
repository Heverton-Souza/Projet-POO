from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import CharacterStatus
from app.domain.errors import ConflictError, ValidationError

from .attributes import Attributes


ATTRIBUTE_POINTS_PER_LEVEL = 5


@dataclass
class Character:
    player_id: str
    name: str
    class_id: str
    race_id: str
    health: int
    max_health: int
    energy: int
    max_energy: int
    attributes: Attributes
    id: str | None = None
    class_name: str = ""
    race_name: str = ""
    level: int = 1
    experience: int = 0
    attribute_points: int = 0
    coins: int = 0
    status: CharacterStatus = CharacterStatus.ACTIVE
    skill_ids: list[str] = field(default_factory=list)
    skills: list[dict[str, Any]] = field(default_factory=list)
    equipment_bonuses: dict[str, int] = field(
        default_factory=lambda: {"attack": 0, "defense": 0}
    )
    created_at: str | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError("O nome do personagem é obrigatório.")
        if not self.class_id:
            raise ValidationError("A classe do personagem é obrigatória.")
        if not self.race_id:
            raise ValidationError("A raça do personagem é obrigatória.")
        self.status = CharacterStatus(self.status)

    def receive_damage(self, amount: int) -> None:
        self.health = max(0, self.health - max(0, int(amount)))
        if self.health == 0:
            self.status = CharacterStatus.DEFEATED

    def spend_energy(self, amount: int) -> None:
        if amount > self.energy:
            raise ConflictError("Energia insuficiente para usar esta habilidade.")
        self.energy -= amount

    def recover(self) -> None:
        if self.status is not CharacterStatus.DEFEATED:
            raise ConflictError(
                "A recuperação completa está disponível apenas para personagens derrotados."
            )
        self.health = self.max_health
        self.energy = self.max_energy
        self.status = CharacterStatus.ACTIVE

    def experience_for_next_level(self) -> int:
        return self.level * 100

    def gain_experience(self, amount: int) -> list[int]:
        levels: list[int] = []
        self.experience += max(0, int(amount))
        while self.experience >= self.experience_for_next_level():
            self.experience -= self.experience_for_next_level()
            self.level += 1
            self.attribute_points += ATTRIBUTE_POINTS_PER_LEVEL
            self.max_health += 10 + self.attributes.vitality
            self.max_energy += 5 + self.attributes.intelligence // 2
            self.health = self.max_health
            self.energy = self.max_energy
            levels.append(self.level)
        return levels

    def distribute_attribute(self, name: str, points: int) -> None:
        if points > self.attribute_points:
            raise ConflictError("Pontos de atributo insuficientes.")
        self.attributes.increase(name, points)
        self.attribute_points -= points
        if name == "vitality":
            gained_health = points * 2
            self.max_health += gained_health
            self.health += gained_health
        if name == "intelligence":
            self.max_energy += points
            self.energy += points

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "playerId": self.player_id,
            "name": self.name,
            "classId": self.class_id,
            "className": self.class_name,
            "raceId": self.race_id,
            "raceName": self.race_name,
            "level": self.level,
            "experience": self.experience,
            "health": self.health,
            "maxHealth": self.max_health,
            "energy": self.energy,
            "maxEnergy": self.max_energy,
            "attributes": self.attributes.to_dict(),
            "attributePoints": self.attribute_points,
            "coins": self.coins,
            "status": self.status.value,
            "skillIds": self.skill_ids,
            "skills": self.skills,
            "equipmentBonuses": self.equipment_bonuses,
            "createdAt": self.created_at,
        }
