from typing import Any

from app.domain.errors import NotFoundError
from app.domain.events import DomainEvent
from app.domain.patterns import CharacterBuilder

from app.application.ports import CatalogRepository, CharacterRepository, EventPublisher


class CreateCharacterUseCase:
    """UC01 — cria um personagem e o vincula ao jogador autenticado."""

    def __init__(
        self,
        characters: CharacterRepository,
        catalog: CatalogRepository,
        events: EventPublisher,
    ) -> None:
        self.characters = characters
        self.catalog = catalog
        self.events = events

    def execute(
        self,
        user: dict[str, Any],
        name: str,
        class_id: str,
        race_id: str,
    ) -> dict[str, Any]:
        character_class = self.catalog.find_class_with_skills(class_id)
        race = self.catalog.find_race_with_skills(race_id)
        if not character_class:
            raise NotFoundError("Classe")
        if not race:
            raise NotFoundError("Raça")

        character = (
            CharacterBuilder()
            .owned_by(user["id"])
            .named(name)
            .from_class(character_class)
            .from_race(race)
            .build()
        )
        created = self.characters.create_character(character)
        self.events.publish(
            DomainEvent(
                "CHARACTER_CREATED",
                user["id"],
                created.id,
                f"Personagem {created.name} criado como {character_class['name']} da raça {race['name']}.",
                {"classId": class_id, "raceId": race_id},
            )
        )
        return created.to_dict()
