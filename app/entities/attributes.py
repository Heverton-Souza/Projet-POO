from dataclasses import dataclass
from typing import Any

from app.domain.errors import ValidationError


ATTRIBUTE_FIELDS = ("strength", "defense", "agility", "intelligence", "vitality", "charisma")


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
        return Attributes.from_dict(
            {
                name: getattr(self, name) + int(modifiers.get(name, 0))
                for name in ATTRIBUTE_FIELDS
            }
        )

    def increase(self, name: str, points: int) -> None:
        if name not in ATTRIBUTE_FIELDS:
            raise ValidationError("Atributo inválido.")
        if isinstance(points, bool) or not isinstance(points, int) or points <= 0:
            raise ValidationError("A quantidade de pontos deve ser um inteiro positivo.")
        setattr(self, name, getattr(self, name) + points)

    def to_dict(self) -> dict[str, int]:
        return {name: getattr(self, name) for name in ATTRIBUTE_FIELDS}
