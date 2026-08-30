from typing import Any

from app.entities import Character, MissionProgress
from app.domain.enums import CharacterStatus, ItemType, UserRole
from app.domain.errors import ConflictError, NotFoundError, ValidationError
from app.domain.events import DomainEvent

from .authorization import AuthorizationPolicy
from .helpers import get_accessible_character, publish_level_events
from .ports import (
    CatalogRepository,
    CharacterRepository,
    EventPublisher,
    HistoryRepository,
    InventoryRepository,
    MissionRepository,
    UserRepository,
)


class CharacterService:
    def __init__(
        self,
        characters: CharacterRepository,
        events: EventPublisher,
        authorization: AuthorizationPolicy,
    ) -> None:
        self.characters = characters
        self.events = events
        self.authorization = authorization

    def list_mine(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        return [character.to_dict() for character in self.characters.list_characters_by_player(user["id"])]

    def get_entity(self, user: dict[str, Any], character_id: str) -> Character:
        return get_accessible_character(self.characters, self.authorization, user, character_id)

    def get(self, user: dict[str, Any], character_id: str) -> dict[str, Any]:
        return self.get_entity(user, character_id).to_dict()

    def distribute_attribute(
        self, user: dict[str, Any], character_id: str, attribute: str, points: int
    ) -> dict[str, Any]:
        character = self.get_entity(user, character_id)
        if character.status is CharacterStatus.IN_COMBAT:
            raise ConflictError("Não é possível distribuir atributos durante um combate.")
        if isinstance(points, bool) or not isinstance(points, int):
            raise ValidationError("A quantidade de pontos deve ser inteira.")
        character.distribute_attribute(attribute, points)
        saved = self.characters.save_character(character)
        self.events.publish(
            DomainEvent(
                "ATTRIBUTE_DISTRIBUTED",
                user["id"],
                character.id,
                f"{points} ponto(s) distribuído(s) em {attribute}.",
                {"attribute": attribute, "points": points},
            )
        )
        return saved.to_dict()

    def recover(self, user: dict[str, Any], character_id: str) -> dict[str, Any]:
        character = self.get_entity(user, character_id)
        character.recover()
        saved = self.characters.save_character(character)
        self.events.publish(
            DomainEvent(
                "CHARACTER_RECOVERED",
                user["id"],
                character.id,
                f"{character.name} descansou e se recuperou da derrota.",
            )
        )
        return saved.to_dict()


class MissionService:
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

    def list_available(self, user: dict[str, Any], character_id: str) -> list[dict[str, Any]]:
        character = self._character(user, character_id)
        return self.missions.list_available_missions(character.id or "")

    def list_mine(self, user: dict[str, Any], character_id: str) -> list[dict[str, Any]]:
        character = self._character(user, character_id)
        return [item.to_dict() for item in self.missions.list_character_missions(character.id or "")]

    def update(self, user: dict[str, Any], progress_id: str, amount: int = 1) -> dict[str, Any]:
        progress = self._progress(user, progress_id)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValidationError("O progresso deve ser um inteiro positivo.")
        progress.update(amount)
        character = self.characters.find_character(progress.character_id)
        assert character is not None
        character.status = CharacterStatus.ON_MISSION
        self.characters.save_character(character)
        return self.missions.save_mission_progress(progress).to_dict()

    def complete(self, user: dict[str, Any], progress_id: str) -> dict[str, Any]:
        progress = self._progress(user, progress_id)
        character = self.characters.find_character(progress.character_id)
        mission = self.missions.find_mission(progress.mission_id)
        assert character is not None and mission is not None
        progress.complete()
        levels = character.gain_experience(mission["rewardExperience"])
        character.coins += mission["rewardCoins"]
        character.status = CharacterStatus.ACTIVE
        self.missions.complete_mission(progress, character, mission)
        self.events.publish(
            DomainEvent(
                "MISSION_COMPLETED",
                user["id"],
                character.id,
                f"Missão \"{mission['title']}\" concluída.",
                {
                    "missionId": mission["id"],
                    "experience": mission["rewardExperience"],
                    "coins": mission["rewardCoins"],
                },
            )
        )
        publish_level_events(self.events, user, character, levels)
        return {
            "progress": progress.to_dict(),
            "character": character.to_dict(),
            "levelsGained": levels,
        }

    def cancel(self, user: dict[str, Any], progress_id: str) -> dict[str, Any]:
        progress = self._progress(user, progress_id)
        progress.cancel()
        character = self.characters.find_character(progress.character_id)
        assert character is not None
        if character.status is CharacterStatus.ON_MISSION:
            character.status = CharacterStatus.ACTIVE
            self.characters.save_character(character)
        return self.missions.save_mission_progress(progress).to_dict()

    def _character(self, user: dict[str, Any], character_id: str) -> Character:
        return get_accessible_character(self.characters, self.authorization, user, character_id)

    def _progress(self, user: dict[str, Any], progress_id: str) -> MissionProgress:
        progress = self.missions.find_mission_progress(progress_id)
        if not progress:
            raise NotFoundError("Progresso da missão")
        self._character(user, progress.character_id)
        return progress

class InventoryService:
    def __init__(
        self,
        inventory: InventoryRepository,
        characters: CharacterRepository,
        catalog: CatalogRepository,
        events: EventPublisher,
        authorization: AuthorizationPolicy,
    ) -> None:
        self.inventory = inventory
        self.characters = characters
        self.catalog = catalog
        self.events = events
        self.authorization = authorization

    def list(self, user: dict[str, Any], character_id: str) -> list[dict[str, Any]]:
        self._character(user, character_id)
        return self.inventory.list_inventory(character_id)

    def grant(
        self, user: dict[str, Any], character_id: str, item_id: str, quantity: int = 1
    ) -> dict[str, Any]:
        self.authorization.require_game_master(user)
        character = self._character(user, character_id)
        item = self.catalog.find_catalog("items", item_id)
        if not item:
            raise NotFoundError("Item")
        quantity = self._quantity(quantity)
        entry = self.inventory.add_inventory_item(character.id or "", item_id, quantity)
        self.events.publish(
            DomainEvent(
                "ITEM_ACQUIRED",
                user["id"],
                character.id,
                f"{quantity}x {item['name']} adicionado(s) ao inventário.",
                {"itemId": item_id, "quantity": quantity},
            )
        )
        return entry

    def remove(
        self, user: dict[str, Any], character_id: str, item_id: str, quantity: int = 1
    ) -> dict[str, Any] | None:
        character = self._character(user, character_id)
        return self.inventory.remove_inventory_item(character.id or "", item_id, self._quantity(quantity))

    def equip(self, user: dict[str, Any], character_id: str, item_id: str) -> dict[str, Any]:
        character = self._character(user, character_id)
        item = self.catalog.find_catalog("items", item_id)
        entry = self.inventory.find_inventory_item(character.id or "", item_id)
        if not item or not entry:
            raise NotFoundError("Item do inventário")
        if item["type"] in {ItemType.POTION.value, ItemType.QUEST.value}:
            raise ConflictError("Este tipo de item não pode ser equipado.")
        if item["minLevel"] > character.level:
            raise ConflictError(f"O item exige nível {item['minLevel']}.")
        if item["requiredClassId"] and item["requiredClassId"] != character.class_id:
            raise ConflictError("O item é incompatível com a classe do personagem.")
        return self.inventory.equip_inventory_item(character.id or "", item_id, True)

    def unequip(self, user: dict[str, Any], character_id: str, item_id: str) -> dict[str, Any]:
        character = self._character(user, character_id)
        return self.inventory.equip_inventory_item(character.id or "", item_id, False)

    def use(self, user: dict[str, Any], character_id: str, item_id: str) -> dict[str, Any]:
        character = self._character(user, character_id)
        item = self.catalog.find_catalog("items", item_id)
        entry = self.inventory.find_inventory_item(character.id or "", item_id)
        if not item or not entry:
            raise NotFoundError("Item do inventário")
        if item["type"] != ItemType.POTION.value:
            raise ConflictError("Somente itens consumíveis podem ser usados.")
        character.health = min(character.max_health, character.health + item["effectHealth"])
        character.energy = min(character.max_energy, character.energy + item["effectEnergy"])
        self.characters.save_character(character)
        self.inventory.remove_inventory_item(character.id or "", item_id, 1)
        self.events.publish(
            DomainEvent("ITEM_USED", user["id"], character.id, f"{item['name']} foi consumido.", {"itemId": item_id})
        )
        return character.to_dict()

    def _character(self, user: dict[str, Any], character_id: str) -> Character:
        return get_accessible_character(self.characters, self.authorization, user, character_id)

    @staticmethod
    def _quantity(quantity: int) -> int:
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValidationError("Quantidade inválida.")
        return quantity


class AdminService:
    def __init__(
        self,
        catalog: CatalogRepository,
        users: UserRepository,
        characters: CharacterRepository,
        authorization: AuthorizationPolicy,
    ) -> None:
        self.catalog = catalog
        self.users = users
        self.characters = characters
        self.authorization = authorization

    def list_catalog(self, resource: str) -> list[dict[str, Any]]:
        return self.catalog.list_catalog(resource)

    def create(self, user: dict[str, Any], resource: str, data: dict[str, Any]) -> dict[str, Any]:
        self.authorization.require_game_master(user)
        return self.catalog.create_catalog(resource, data, user["id"])

    def update(
        self, user: dict[str, Any], resource: str, item_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        self.authorization.require_game_master(user)
        if not self.catalog.find_catalog(resource, item_id):
            raise NotFoundError("Registro")
        return self.catalog.update_catalog(resource, item_id, data)

    def remove(self, user: dict[str, Any], resource: str, item_id: str) -> None:
        self.authorization.require_game_master(user)
        if not self.catalog.find_catalog(resource, item_id):
            raise NotFoundError("Registro")
        self.catalog.delete_catalog(resource, item_id)

    def list_users(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        self.authorization.require_game_master(user)
        return [
            {key: value for key, value in item.items() if key != "passwordHash"}
            for item in self.users.list_users()
        ]

    def list_characters(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        self.authorization.require_game_master(user)
        return [character.to_dict() for character in self.characters.list_all_characters()]

    def update_user_role(self, user: dict[str, Any], user_id: str, role: str) -> dict[str, Any]:
        self.authorization.require_administrator(user)
        try:
            role = UserRole(role).value
        except ValueError:
            raise ValidationError("Perfil de usuário inválido.")
        if not self.users.find_user(user_id):
            raise NotFoundError("Usuário")
        updated = self.users.update_user_role(user_id, role)
        return {key: value for key, value in updated.items() if key != "passwordHash"}


class HistoryService:
    def __init__(
        self,
        history: HistoryRepository,
        characters: CharacterRepository,
        authorization: AuthorizationPolicy,
    ) -> None:
        self.history = history
        self.characters = characters
        self.authorization = authorization

    def list(self, user: dict[str, Any], character_id: str) -> list[dict[str, Any]]:
        get_accessible_character(self.characters, self.authorization, user, character_id)
        return self.history.list_history(character_id)
