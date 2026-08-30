from datetime import UTC, datetime
from typing import Any

from app.entities import Character
from app.domain.enums import CharacterStatus, CombatStatus
from app.domain.errors import ConflictError, NotFoundError
from app.domain.events import DomainEvent
from app.domain.patterns import select_attack_strategy

from app.application.authorization import AuthorizationPolicy
from app.application.helpers import get_accessible_character, publish_level_events
from app.application.ports import (
    CatalogRepository,
    CharacterRepository,
    CombatRepository,
    DiceRoller,
    EventPublisher,
    IdGenerator,
)


class PerformCombatUseCase:
    """UC03 — inicia o combate e executa seus turnos até o encerramento."""

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

    def execute(
        self,
        user: dict[str, Any],
        combat_id: str,
        action: str,
        skill_id: str | None = None,
    ) -> dict[str, Any]:
        combat = self.combats.find_combat(combat_id)
        if not combat:
            raise NotFoundError("Combate")
        if combat["status"] != CombatStatus.IN_PROGRESS.value:
            raise ConflictError("Este combate já foi finalizado.")

        character = self._character(user, combat["characterId"])
        enemy = self.catalog.find_catalog("enemies", combat["enemyId"])
        if not enemy:
            raise NotFoundError("Inimigo")
        now = datetime.now(UTC).isoformat()

        if action == "FUGIR":
            return self._flee(user, combat, character, enemy, now)

        turn = self._player_turn(character, enemy, action, skill_id, now)
        combat["enemyHealth"] = max(0, combat["enemyHealth"] - turn["damage"])
        levels = self._resolve_turn(combat, character, enemy, turn, now)

        combat = self.combats.save_combat_turn(combat, turn, character)
        self._publish_result(user, character, enemy, combat)
        publish_level_events(self.events, user, character, levels)
        return {
            "combat": combat,
            "character": character.to_dict(),
            "turn": turn,
            "levelsGained": levels,
        }

    def _flee(
        self,
        user: dict[str, Any],
        combat: dict[str, Any],
        character: Character,
        enemy: dict[str, Any],
        now: str,
    ) -> dict[str, Any]:
        combat.update(status=CombatStatus.FLED.value, finishedAt=now)
        character.status = CharacterStatus.ACTIVE
        turn = {
            "actor": "PERSONAGEM",
            "action": "FUGIR",
            "damage": 0,
            "enemyDamage": 0,
            "occurredAt": now,
        }
        saved = self.combats.save_combat_turn(combat, turn, character)
        self.events.publish(
            DomainEvent(
                "COMBAT_FLED",
                user["id"],
                character.id,
                f"Fuga do combate contra {enemy['name']}.",
                {"combatId": combat["id"]},
            )
        )
        return {
            "combat": saved,
            "character": character.to_dict(),
            "turn": turn,
            "levelsGained": [],
        }

    def _player_turn(
        self,
        character: Character,
        enemy: dict[str, Any],
        action: str,
        skill_id: str | None,
        now: str,
    ) -> dict[str, Any]:
        skill = None
        if action == "HABILIDADE":
            if not skill_id or skill_id not in character.skill_ids:
                raise ConflictError("O personagem não possui esta habilidade.")
            skill = self.catalog.find_catalog("skills", skill_id)

        result = select_attack_strategy(action, skill).execute(
            character,
            {"defense": enemy["defense"]},
        )
        character.spend_energy(result["energyCost"])
        roll, hit_chance, hit = self._roll_attack(
            character.attributes.agility,
            enemy["agility"],
        )
        return {
            "actor": "PERSONAGEM",
            "action": result["label"],
            "damage": result["damage"] if hit else 0,
            "enemyDamage": 0,
            "playerRoll": roll,
            "playerHitChance": hit_chance,
            "playerHit": hit,
            "enemyRoll": None,
            "enemyHitChance": None,
            "enemyHit": None,
            "occurredAt": now,
        }

    def _resolve_turn(
        self,
        combat: dict[str, Any],
        character: Character,
        enemy: dict[str, Any],
        turn: dict[str, Any],
        now: str,
    ) -> list[int]:
        if combat["enemyHealth"] == 0:
            combat.update(status=CombatStatus.VICTORY.value, finishedAt=now)
            character.status = CharacterStatus.ACTIVE
            character.coins += enemy["rewardCoins"]
            turn["rewardItemId"] = enemy["rewardItemId"]
            return character.gain_experience(enemy["rewardExperience"])

        roll, hit_chance, hit = self._roll_attack(
            enemy["agility"],
            character.attributes.agility,
        )
        turn.update(enemyRoll=roll, enemyHitChance=hit_chance, enemyHit=hit)
        if hit:
            turn["enemyDamage"] = max(
                1,
                enemy["strength"]
                - character.attributes.defense
                - character.equipment_bonuses.get("defense", 0),
            )
            character.receive_damage(turn["enemyDamage"])
        if character.health == 0:
            combat.update(status=CombatStatus.DEFEAT.value, finishedAt=now)
        return []

    def _publish_result(
        self,
        user: dict[str, Any],
        character: Character,
        enemy: dict[str, Any],
        combat: dict[str, Any],
    ) -> None:
        if combat["status"] == CombatStatus.IN_PROGRESS.value:
            return
        won = combat["status"] == CombatStatus.VICTORY.value
        self.events.publish(
            DomainEvent(
                "COMBAT_WON" if won else "COMBAT_LOST",
                user["id"],
                character.id,
                f"{'Vitória' if won else 'Derrota'} contra {enemy['name']}.",
                {"combatId": combat["id"]},
            )
        )

    def _roll_attack(self, attacker_agility: int, defender_agility: int) -> tuple[int, int, bool]:
        roll = self.dice_roller.roll_d100()
        return (
            roll,
            self._hit_chance(attacker_agility, defender_agility),
            self._attack_hits(roll, attacker_agility, defender_agility),
        )

    @classmethod
    def _attack_hits(cls, roll: int, attacker_agility: int, defender_agility: int) -> bool:
        return roll + attacker_agility - defender_agility > cls.HIT_THRESHOLD

    @classmethod
    def _hit_chance(cls, attacker_agility: int, defender_agility: int) -> int:
        highest_miss = cls.HIT_THRESHOLD - attacker_agility + defender_agility
        return cls.D100_MAX - max(0, min(cls.D100_MAX, highest_miss))

    def _character(self, user: dict[str, Any], character_id: str) -> Character:
        return get_accessible_character(
            self.characters,
            self.authorization,
            user,
            character_id,
        )
