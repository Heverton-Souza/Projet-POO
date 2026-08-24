from datetime import UTC, datetime
from typing import Any

from app.domain.entities import Character, MissionProgress
from app.domain.enums import CharacterStatus, CombatStatus, ItemType, MissionStatus, UserRole
from app.domain.errors import ConflictError, NotFoundError, ValidationError
from app.domain.events import DomainEvent
from app.domain.patterns import CharacterBuilder, select_attack_strategy

from .authorization import AuthorizationPolicy
from .ports import (
    CatalogRepository,
    CharacterRepository,
    CombatRepository,
    DiceRoller,
    EventPublisher,
    HistoryRepository,
    IdGenerator,
    InventoryRepository,
    MissionRepository,
    UserRepository,
)


class CharacterService:
    def __init__(
        self,
        characters: CharacterRepository,
        catalog: CatalogRepository,
        events: EventPublisher,
        authorization: AuthorizationPolicy,
    ) -> None:
        self.characters = characters
        self.catalog = catalog
        self.events = events
        self.authorization = authorization

    def create(self, user: dict[str, Any], name: str, class_id: str, race_id: str) -> dict[str, Any]:
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

    def list_mine(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        return [character.to_dict() for character in self.characters.list_characters_by_player(user["id"])]

    def get_entity(self, user: dict[str, Any], character_id: str) -> Character:
        character = self.characters.find_character(character_id)
        if not character:
            raise NotFoundError("Personagem")
        self.authorization.require_character_owner(user, character)
        return character

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

    def accept(self, user: dict[str, Any], character_id: str, mission_id: str) -> dict[str, Any]:
        character = self._character(user, character_id)
        mission = self.missions.find_mission(mission_id)
        if not mission:
            raise NotFoundError("Missão")
        if mission["status"] != MissionStatus.AVAILABLE.value:
            raise ConflictError("A missão não está disponível.")
        if character.level < mission["minLevel"]:
            raise ConflictError(f"O personagem precisa estar no nível {mission['minLevel']}.")
        progress = self.missions.accept_mission(character.id or "", mission_id)
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
        self._publish_levels(user, character, levels)
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
        character = self.characters.find_character(character_id)
        if not character:
            raise NotFoundError("Personagem")
        self.authorization.require_character_owner(user, character)
        return character

    def _progress(self, user: dict[str, Any], progress_id: str) -> MissionProgress:
        progress = self.missions.find_mission_progress(progress_id)
        if not progress:
            raise NotFoundError("Progresso da missão")
        self._character(user, progress.character_id)
        return progress

    def _publish_levels(self, user: dict[str, Any], character: Character, levels: list[int]) -> None:
        for level in levels:
            self.events.publish(
                DomainEvent(
                    "LEVEL_UP",
                    user["id"],
                    character.id,
                    f"{character.name} alcançou o nível {level}.",
                    {"level": level},
                )
            )


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
        character = self.characters.find_character(character_id)
        if not character:
            raise NotFoundError("Personagem")
        self.authorization.require_character_owner(user, character)
        return character

    @staticmethod
    def _quantity(quantity: int) -> int:
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValidationError("Quantidade inválida.")
        return quantity


class CombatService:
    HIT_THRESHOLD = 70
    D100_MAX = 100

    def __init__(
        self,
        combats: CombatRepository,
        characters: CharacterRepository,
        catalog: CatalogRepository,
        events: EventPublisher,
        authorization: AuthorizationPolicy,
        id_generator: IdGenerator,
        dice_roller: DiceRoller,
    ) -> None:
        self.combats = combats
        self.characters = characters
        self.catalog = catalog
        self.events = events
        self.authorization = authorization
        self.id_generator = id_generator
        self.dice_roller = dice_roller

    def list(self, user: dict[str, Any], character_id: str) -> list[dict[str, Any]]:
        self._character(user, character_id)
        return self.combats.list_character_combats(character_id)

    def start(self, user: dict[str, Any], character_id: str, enemy_id: str) -> dict[str, Any]:
        character = self._character(user, character_id)
        if character.status not in {CharacterStatus.ACTIVE, CharacterStatus.ON_MISSION}:
            raise ConflictError("Somente personagens ativos ou em missão podem iniciar um combate.")
        enemy = self.catalog.find_catalog("enemies", enemy_id)
        if not enemy:
            raise NotFoundError("Inimigo")
        combat = {
            "id": self.id_generator.generate(),
            "characterId": character_id,
            "enemyId": enemy_id,
            "status": CombatStatus.IN_PROGRESS.value,
            "enemyHealth": enemy["health"],
            "enemyMaxHealth": enemy["health"],
            "startedAt": datetime.now(UTC).isoformat(),
            "finishedAt": None,
        }
        character.status = CharacterStatus.IN_COMBAT
        created = self.combats.create_combat(combat, character)
        self.events.publish(
            DomainEvent(
                "COMBAT_STARTED",
                user["id"],
                character.id,
                f"Combate iniciado contra {enemy['name']}.",
                {"combatId": created["id"], "enemyId": enemy_id},
            )
        )
        return created

    def act(
        self, user: dict[str, Any], combat_id: str, action: str, skill_id: str | None = None
    ) -> dict[str, Any]:
        combat = self.combats.find_combat(combat_id)
        if not combat:
            raise NotFoundError("Combate")
        if combat["status"] != CombatStatus.IN_PROGRESS.value:
            raise ConflictError("Este combate já foi finalizado.")
        character = self._character(user, combat["characterId"])
        enemy = self.catalog.find_catalog("enemies", combat["enemyId"])
        assert enemy is not None
        now = datetime.now(UTC).isoformat()

        if action == "FUGIR":
            combat.update(status=CombatStatus.FLED.value, finishedAt=now)
            character.status = CharacterStatus.ACTIVE
            turn = {"actor": "PERSONAGEM", "action": "FUGIR", "damage": 0, "enemyDamage": 0, "occurredAt": now}
            combat = self.combats.save_combat_turn(combat, turn, character)
            self.events.publish(
                DomainEvent("COMBAT_FLED", user["id"], character.id, f"Fuga do combate contra {enemy['name']}.", {"combatId": combat_id})
            )
            return {"combat": combat, "character": character.to_dict(), "turn": turn, "levelsGained": []}

        skill = None
        if action == "HABILIDADE":
            if not skill_id or skill_id not in character.skill_ids:
                raise ConflictError("O personagem não possui esta habilidade.")
            skill = self.catalog.find_catalog("skills", skill_id)
        result = select_attack_strategy(action, skill).execute(character, {"defense": enemy["defense"]})
        character.spend_energy(result["energyCost"])
        player_hit_chance = self._hit_chance(
            character.attributes.agility,
            enemy["agility"],
        )
        player_roll = self.dice_roller.roll_d100()
        player_hit = self._attack_hits(
            player_roll,
            character.attributes.agility,
            enemy["agility"],
        )
        player_damage = result["damage"] if player_hit else 0
        combat["enemyHealth"] = max(0, combat["enemyHealth"] - player_damage)
        turn = {
            "actor": "PERSONAGEM",
            "action": result["label"],
            "damage": player_damage,
            "enemyDamage": 0,
            "playerRoll": player_roll,
            "playerHitChance": player_hit_chance,
            "playerHit": player_hit,
            "enemyRoll": None,
            "enemyHitChance": None,
            "enemyHit": None,
            "occurredAt": now,
        }
        levels: list[int] = []

        if combat["enemyHealth"] == 0:
            combat.update(status=CombatStatus.VICTORY.value, finishedAt=now)
            character.status = CharacterStatus.ACTIVE
            levels.extend(character.gain_experience(enemy["rewardExperience"]))
            character.coins += enemy["rewardCoins"]
            turn["rewardItemId"] = enemy["rewardItemId"]
        else:
            enemy_hit_chance = self._hit_chance(
                enemy["agility"],
                character.attributes.agility,
            )
            enemy_roll = self.dice_roller.roll_d100()
            enemy_hit = self._attack_hits(
                enemy_roll,
                enemy["agility"],
                character.attributes.agility,
            )
            turn.update(
                enemyRoll=enemy_roll,
                enemyHitChance=enemy_hit_chance,
                enemyHit=enemy_hit,
            )
            if enemy_hit:
                turn["enemyDamage"] = max(
                    1,
                    enemy["strength"]
                    - character.attributes.defense
                    - character.equipment_bonuses.get("defense", 0),
                )
                character.receive_damage(turn["enemyDamage"])
            if character.health == 0:
                combat.update(status=CombatStatus.DEFEAT.value, finishedAt=now)

        combat = self.combats.save_combat_turn(combat, turn, character)
        if combat["status"] != CombatStatus.IN_PROGRESS.value:
            won = combat["status"] == CombatStatus.VICTORY.value
            self.events.publish(
                DomainEvent(
                    "COMBAT_WON" if won else "COMBAT_LOST",
                    user["id"],
                    character.id,
                    f"{'Vitória' if won else 'Derrota'} contra {enemy['name']}.",
                    {"combatId": combat_id},
                )
            )
        for level in levels:
            self.events.publish(
                DomainEvent("LEVEL_UP", user["id"], character.id, f"{character.name} alcançou o nível {level}.", {"level": level})
            )
        return {"combat": combat, "character": character.to_dict(), "turn": turn, "levelsGained": levels}

    @classmethod
    def _attack_hits(
        cls,
        roll: int,
        attacker_agility: int,
        defender_agility: int,
    ) -> bool:
        adjusted_roll = roll + attacker_agility - defender_agility
        return adjusted_roll > cls.HIT_THRESHOLD

    @classmethod
    def _hit_chance(cls, attacker_agility: int, defender_agility: int) -> int:
        highest_miss = cls.HIT_THRESHOLD - attacker_agility + defender_agility
        return cls.D100_MAX - max(0, min(cls.D100_MAX, highest_miss))

    def _character(self, user: dict[str, Any], character_id: str) -> Character:
        character = self.characters.find_character(character_id)
        if not character:
            raise NotFoundError("Personagem")
        self.authorization.require_character_owner(user, character)
        return character


class AdminService:
    RESOURCES = {"classes", "races", "skills", "items", "missions", "enemies"}

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
        self._resource(resource)
        return self.catalog.list_catalog(resource)

    def create(self, user: dict[str, Any], resource: str, data: dict[str, Any]) -> dict[str, Any]:
        self.authorization.require_game_master(user)
        self._resource(resource)
        return self.catalog.create_catalog(resource, data, user["id"])

    def update(
        self, user: dict[str, Any], resource: str, item_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        self.authorization.require_game_master(user)
        self._resource(resource)
        if not self.catalog.find_catalog(resource, item_id):
            raise NotFoundError("Registro")
        return self.catalog.update_catalog(resource, item_id, data)

    def remove(self, user: dict[str, Any], resource: str, item_id: str) -> None:
        self.authorization.require_game_master(user)
        self._resource(resource)
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
        if role not in {item.value for item in UserRole}:
            raise ValidationError("Perfil de usuário inválido.")
        if not self.users.find_user(user_id):
            raise NotFoundError("Usuário")
        updated = self.users.update_user_role(user_id, role)
        return {key: value for key, value in updated.items() if key != "passwordHash"}

    def _resource(self, resource: str) -> None:
        if resource not in self.RESOURCES:
            raise NotFoundError("Catálogo")


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
        character = self.characters.find_character(character_id)
        if not character:
            raise NotFoundError("Personagem")
        self.authorization.require_character_owner(user, character)
        return self.history.list_history(character_id)
