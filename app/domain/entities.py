from dataclasses import dataclass, field
from typing import Any

from .enums import CharacterStatus, MissionStatus
from .errors import ConflictError, ValidationError


ATTRIBUTE_FIELDS = ("strength", "defense", "agility", "intelligence", "vitality", "charisma")
ATTRIBUTE_POINTS_PER_LEVEL = 5


@dataclass
class Attributes:
    strength: int = 0
    defense: int = 0
    agility: int = 0
    intelligence: int = 0
    vitality: int = 0
    charisma: int = 0

    @classmethod
    def from_dict(cls, values: dict[str, Any] | None = None) -> "Attributes":
        values = values or {}
        parsed: dict[str, int] = {}
        for name in ATTRIBUTE_FIELDS:
            value = values.get(name, 0)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(f"O atributo {name} deve ser um número inteiro.")
            parsed[name] = value
        return cls(**parsed)

    def add(self, modifiers: dict[str, Any] | None = None) -> "Attributes":
        modifiers = modifiers or {}
        return Attributes.from_dict({name: getattr(self, name) + int(modifiers.get(name, 0)) for name in ATTRIBUTE_FIELDS})

    def increase(self, name: str, points: int) -> None:
        if name not in ATTRIBUTE_FIELDS:
            raise ValidationError("Atributo inválido.")
        if isinstance(points, bool) or not isinstance(points, int) or points <= 0:
            raise ValidationError("A quantidade de pontos deve ser um inteiro positivo.")
        setattr(self, name, getattr(self, name) + points)

    def to_dict(self) -> dict[str, int]:
        return {name: getattr(self, name) for name in ATTRIBUTE_FIELDS}


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
    equipment_bonuses: dict[str, int] = field(default_factory=lambda: {"attack": 0, "defense": 0})
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
            raise ConflictError("A recuperação completa está disponível apenas para personagens derrotados.")
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


@dataclass
class MissionProgress:
    id: str
    character_id: str
    mission_id: str
    target: int
    status: MissionStatus = MissionStatus.ACCEPTED
    progress: int = 0
    accepted_at: str | None = None
    completed_at: str | None = None
    title: str = ""
    objective: str = ""

    def __post_init__(self) -> None:
        self.status = MissionStatus(self.status)

    def update(self, amount: int) -> None:
        if self.status not in {MissionStatus.ACCEPTED, MissionStatus.IN_PROGRESS}:
            raise ConflictError("Esta missão não permite atualização de progresso.")
        self.status = MissionStatus.IN_PROGRESS
        self.progress = min(self.target, self.progress + max(0, amount))

    def complete(self) -> None:
        if self.progress < self.target:
            raise ConflictError("Todos os objetivos devem ser cumpridos antes de concluir a missão.")
        self.status = MissionStatus.COMPLETED

    def cancel(self) -> None:
        if self.status in {MissionStatus.COMPLETED, MissionStatus.CANCELLED}:
            raise ConflictError("Esta missão já foi finalizada.")
        self.status = MissionStatus.CANCELLED

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "characterId": self.character_id,
            "missionId": self.mission_id,
            "status": self.status.value,
            "progress": self.progress,
            "target": self.target,
            "acceptedAt": self.accepted_at,
            "completedAt": self.completed_at,
            "title": self.title,
            "objective": self.objective,
        }
