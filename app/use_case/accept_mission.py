from typing import Any

from app.domain.enums import CharacterStatus, MissionStatus
from app.domain.errors import ConflictError, NotFoundError
from app.domain.events import DomainEvent

from app.application.authorization import AuthorizationPolicy
from app.application.helpers import get_accessible_character
from app.application.ports import CharacterRepository, EventPublisher, MissionRepository


class AcceptMissionUseCase:
    """UC02 — valida e associa uma missão disponível ao personagem."""

    def __init__(
        self,
        missions: MissionRepository,
        characters: CharacterRepository,
        events: EventPublisher,
        authorization: AuthorizationPolicy,
    ) -> None:
        self.missions = missions
        self.characters = characters
        self.events = events
        self.authorization = authorization

    def execute(
        self,
        user: dict[str, Any],
        character_id: str,
        mission_id: str,
    ) -> dict[str, Any]:
        character = get_accessible_character(
            self.characters,
            self.authorization,
            user,
            character_id,
        )
        mission = self.missions.find_mission(mission_id)
        if not mission:
            raise NotFoundError("Missão")
        if mission["status"] != MissionStatus.AVAILABLE.value:
            raise ConflictError("A missão não está disponível.")
        if character.level < mission["minLevel"]:
            raise ConflictError(f"O personagem precisa estar no nível {mission['minLevel']}.")

        character.status = CharacterStatus.ON_MISSION
        progress = self.missions.accept_mission(character, mission_id)
        self.events.publish(
            DomainEvent(
                "MISSION_ACCEPTED",
                user["id"],
                character.id,
                f"Missão \"{mission['title']}\" aceita.",
                {"missionId": mission_id},
            )
        )
        return progress.to_dict()
