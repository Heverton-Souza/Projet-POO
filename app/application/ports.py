from abc import ABC, abstractmethod
from typing import Any, Callable

from app.entities import Character, MissionProgress
from app.domain.events import DomainEvent


class UserRepository(ABC):
    @abstractmethod
    def find_user_by_email(self, email: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def find_user(self, user_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def create_user(self, user: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def list_users(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def update_user_role(self, user_id: str, role: str) -> dict[str, Any]: ...

    @abstractmethod
    def create_session(self, session: dict[str, Any]) -> None: ...

    @abstractmethod
    def find_valid_session(self, token_hash: str, now: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def delete_session(self, token_hash: str) -> None: ...


class CatalogRepository(ABC):
    @abstractmethod
    def list_catalog(self, resource: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def find_catalog(self, resource: str, item_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def create_catalog(self, resource: str, data: dict[str, Any], actor_id: str) -> dict[str, Any]: ...

    @abstractmethod
    def update_catalog(self, resource: str, item_id: str, data: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def delete_catalog(self, resource: str, item_id: str) -> None: ...

    @abstractmethod
    def find_class_with_skills(self, item_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def find_race_with_skills(self, item_id: str) -> dict[str, Any] | None: ...


class CharacterRepository(ABC):
    @abstractmethod
    def create_character(self, character: Character) -> Character: ...

    @abstractmethod
    def find_character(self, character_id: str) -> Character | None: ...

    @abstractmethod
    def list_characters_by_player(self, player_id: str) -> list[Character]: ...

    @abstractmethod
    def list_all_characters(self) -> list[Character]: ...

    @abstractmethod
    def save_character(self, character: Character) -> Character: ...


class MissionRepository(ABC):
    @abstractmethod
    def list_available_missions(self, character_id: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def find_mission(self, mission_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def accept_mission(self, character: Character, mission_id: str) -> MissionProgress: ...

    @abstractmethod
    def find_mission_progress(self, progress_id: str) -> MissionProgress | None: ...

    @abstractmethod
    def list_character_missions(self, character_id: str) -> list[MissionProgress]: ...

    @abstractmethod
    def save_mission_progress(self, progress: MissionProgress) -> MissionProgress: ...

    @abstractmethod
    def complete_mission(self, progress: MissionProgress, character: Character, mission: dict[str, Any]) -> None: ...


class InventoryRepository(ABC):
    @abstractmethod
    def list_inventory(self, character_id: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def find_inventory_item(self, character_id: str, item_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def add_inventory_item(self, character_id: str, item_id: str, quantity: int) -> dict[str, Any]: ...

    @abstractmethod
    def remove_inventory_item(self, character_id: str, item_id: str, quantity: int) -> dict[str, Any] | None: ...

    @abstractmethod
    def equip_inventory_item(self, character_id: str, item_id: str, equipped: bool) -> dict[str, Any]: ...


class CombatRepository(ABC):
    @abstractmethod
    def create_combat(self, combat: dict[str, Any], character: Character) -> dict[str, Any]: ...

    @abstractmethod
    def find_combat(self, combat_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def save_combat_turn(self, combat: dict[str, Any], turn: dict[str, Any], character: Character) -> dict[str, Any]: ...

    @abstractmethod
    def list_character_combats(self, character_id: str) -> list[dict[str, Any]]: ...


class HistoryRepository(ABC):
    @abstractmethod
    def add_history(self, event: DomainEvent) -> None: ...

    @abstractmethod
    def list_history(self, character_id: str) -> list[dict[str, Any]]: ...


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, plain_text: str) -> str: ...

    @abstractmethod
    def verify(self, plain_text: str, encoded: str) -> bool: ...


class TokenService(ABC):
    @abstractmethod
    def generate(self) -> str: ...

    @abstractmethod
    def hash(self, token: str) -> str: ...


class IdGenerator(ABC):
    @abstractmethod
    def generate(self) -> str: ...


class DiceRoller(ABC):
    @abstractmethod
    def roll_d100(self) -> int: ...


class EventPublisher(ABC):
    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None: ...

    @abstractmethod
    def publish(self, event: DomainEvent) -> None: ...
