from abc import ABC, abstractmethod
from typing import Any

from app.entities import Attributes, Character
from .errors import ConflictError, ValidationError


class CharacterBuilder:
    """Builder: monta um personagem válido aplicando classe e raça em etapas."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {"skill_ids": []}

    def owned_by(self, player_id: str) -> "CharacterBuilder":
        self._data["player_id"] = player_id
        return self

    def named(self, name: str) -> "CharacterBuilder":
        self._data["name"] = name
        return self

    def from_class(self, character_class: dict[str, Any] | None) -> "CharacterBuilder":
        if not character_class:
            raise ValidationError("Classe inválida.")
        self._data["class_id"] = character_class["id"]
        self._data["attributes"] = Attributes.from_dict(character_class["attributes"])
        self._data["max_health"] = character_class["baseHealth"]
        self._data["max_energy"] = character_class["baseEnergy"]
        self._data["skill_ids"].extend(character_class.get("skillIds", []))
        return self

    def from_race(self, race: dict[str, Any] | None) -> "CharacterBuilder":
        if not race:
            raise ValidationError("Raça inválida.")
        self._data["race_id"] = race["id"]
        self._data["attributes"] = self._data.get("attributes", Attributes()).add(race["modifiers"])
        self._data["skill_ids"].extend(race.get("skillIds", []))
        return self

    def build(self) -> Character:
        attributes: Attributes = self._data.get("attributes", Attributes())
        max_health = self._data.get("max_health", 0) + max(0, attributes.vitality) * 2
        max_energy = self._data.get("max_energy", 0) + max(0, attributes.intelligence)
        return Character(
            player_id=self._data.get("player_id", ""),
            name=self._data.get("name", ""),
            class_id=self._data.get("class_id", ""),
            race_id=self._data.get("race_id", ""),
            health=max_health,
            max_health=max_health,
            energy=max_energy,
            max_energy=max_energy,
            attributes=attributes,
            skill_ids=list(dict.fromkeys(self._data["skill_ids"])),
        )


class AttackStrategy(ABC):
    """Interface do Strategy de ataques."""

    @abstractmethod
    def execute(self, attacker: Character, defender: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class BasicAttackStrategy(AttackStrategy):
    def execute(self, attacker: Character, defender: dict[str, Any]) -> dict[str, Any]:
        raw = (
            attacker.attributes.strength
            + attacker.attributes.agility // 2
            + attacker.equipment_bonuses.get("attack", 0)
        )
        return {"damage": max(1, raw - defender["defense"]), "energyCost": 0, "label": "Ataque comum"}


class SkillAttackStrategy(AttackStrategy):
    def __init__(self, skill: dict[str, Any] | None) -> None:
        self.skill = skill

    def execute(self, attacker: Character, defender: dict[str, Any]) -> dict[str, Any]:
        if not self.skill:
            raise ValidationError("Habilidade não encontrada.")
        if attacker.level < self.skill["minLevel"]:
            raise ConflictError(f"A habilidade exige nível {self.skill['minLevel']}.")
        if attacker.energy < self.skill["energyCost"]:
            raise ConflictError("Energia insuficiente para usar esta habilidade.")
        scaling = attacker.attributes.strength if self.skill["type"] == "FISICA" else attacker.attributes.intelligence
        damage = max(
            1,
            self.skill["damage"]
            + scaling
            + attacker.equipment_bonuses.get("attack", 0)
            - defender["defense"],
        )
        return {"damage": damage, "energyCost": self.skill["energyCost"], "label": self.skill["name"]}


def select_attack_strategy(action: str, skill: dict[str, Any] | None = None) -> AttackStrategy:
    if action == "ATAQUE":
        return BasicAttackStrategy()
    if action == "HABILIDADE":
        return SkillAttackStrategy(skill)
    raise ValidationError("Ação de combate inválida.")
