from typing import Any

from app.entities import Character
from app.domain.errors import NotFoundError
from app.domain.events import DomainEvent

from .authorization import AuthorizationPolicy
from .ports import CharacterRepository, EventPublisher


def get_accessible_character(
    characters: CharacterRepository,
    authorization: AuthorizationPolicy,
    user: dict[str, Any],
    character_id: str,
) -> Character:
    """Busca o personagem e garante que o usuário pode acessá-lo."""
    character = characters.find_character(character_id)
    if not character:
        raise NotFoundError("Personagem")
    authorization.require_character_owner(user, character)
    return character


def publish_level_events(
    events: EventPublisher,
    user: dict[str, Any],
    character: Character,
    levels: list[int],
) -> None:
    for level in levels:
        events.publish(
            DomainEvent(
                "LEVEL_UP",
                user["id"],
                character.id,
                f"{character.name} alcançou o nível {level}.",
                {"level": level},
            )
        )
