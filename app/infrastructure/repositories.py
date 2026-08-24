import json
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.application.ports import (
    CatalogRepository,
    CharacterRepository,
    CombatRepository,
    HistoryRepository,
    InventoryRepository,
    MissionRepository,
    UserRepository,
)
from app.domain.entities import ATTRIBUTE_FIELDS, Attributes, Character, MissionProgress
from app.domain.errors import ConflictError, NotFoundError, ValidationError
from app.domain.events import DomainEvent

from .database import Database


CATALOG_TABLES = {
    "classes": ("character_classes", "name"),
    "races": ("races", "name"),
    "skills": ("skills", "name"),
    "items": ("items", "name"),
    "missions": ("missions", "title"),
    "enemies": ("enemies", "name"),
}


class SqliteRepository(
    UserRepository,
    CatalogRepository,
    CharacterRepository,
    MissionRepository,
    InventoryRepository,
    CombatRepository,
    HistoryRepository,
):
    """Implementa os ports usando apenas o sqlite3 da biblioteca padrão."""

    def __init__(self, database: Database) -> None:
        self.db = database

    # Usuários e sessões
    def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self._map_user(self.db.fetchone("SELECT * FROM users WHERE email = ?", (email,)))

    def find_user(self, user_id: str) -> dict[str, Any] | None:
        return self._map_user(self.db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,)))

    def create_user(self, user: dict[str, Any]) -> dict[str, Any]:
        self.db.execute(
            "INSERT INTO users (id, name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user["id"], user["name"], user["email"], user["passwordHash"], user["role"], user["createdAt"]),
        )
        return self.find_user(user["id"]) or user

    def list_users(self) -> list[dict[str, Any]]:
        return [self._map_user(row) for row in self.db.fetchall("SELECT * FROM users ORDER BY created_at DESC")]

    def update_user_role(self, user_id: str, role: str) -> dict[str, Any]:
        self.db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        user = self.find_user(user_id)
        assert user is not None
        return user

    def create_session(self, session: dict[str, Any]) -> None:
        self.db.execute("DELETE FROM sessions WHERE expires_at <= ?", (datetime.now(UTC).isoformat(),))
        self.db.execute(
            "INSERT INTO sessions (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
            (session["id"], session["userId"], session["tokenHash"], session["expiresAt"]),
        )

    def find_valid_session(self, token_hash: str, now: str) -> dict[str, Any] | None:
        row = self.db.fetchone(
            "SELECT * FROM sessions WHERE token_hash = ? AND expires_at > ?", (token_hash, now)
        )
        if not row:
            return None
        return {"id": row["id"], "userId": row["user_id"], "tokenHash": row["token_hash"], "expiresAt": row["expires_at"]}

    def delete_session(self, token_hash: str) -> None:
        self.db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    # Catálogos administrativos
    def list_catalog(self, resource: str) -> list[dict[str, Any]]:
        table, order = self._catalog(resource)
        return [self._map_catalog(resource, row) for row in self.db.fetchall(f"SELECT * FROM {table} ORDER BY {order}")]

    def find_catalog(self, resource: str, item_id: str) -> dict[str, Any] | None:
        table, _ = self._catalog(resource)
        row = self.db.fetchone(f"SELECT * FROM {table} WHERE id = ?", (item_id,))
        return self._map_catalog(resource, row) if row else None

    def create_catalog(self, resource: str, data: dict[str, Any], actor_id: str) -> dict[str, Any]:
        table, _ = self._catalog(resource)
        values = self._normalize_catalog(resource, data)
        item_id = str(uuid4())
        columns = [*values, "created_by"]
        placeholders = ", ".join("?" for _ in range(len(columns) + 1))
        try:
            self.db.execute(
                f"INSERT INTO {table} (id, {', '.join(columns)}) VALUES ({placeholders})",
                (item_id, *values.values(), actor_id),
            )
        except sqlite3.IntegrityError as error:
            self._raise_integrity(error)
        result = self.find_catalog(resource, item_id)
        assert result is not None
        return result

    def update_catalog(self, resource: str, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        table, _ = self._catalog(resource)
        current = self.find_catalog(resource, item_id)
        assert current is not None
        merged = {**current, **data}
        if resource == "classes":
            merged["attributes"] = {**current["attributes"], **data.get("attributes", {})}
        if resource == "races":
            merged["modifiers"] = {**current["modifiers"], **data.get("modifiers", {})}
        values = self._normalize_catalog(resource, merged)
        assignments = ", ".join(f"{column} = ?" for column in values)
        try:
            self.db.execute(f"UPDATE {table} SET {assignments} WHERE id = ?", (*values.values(), item_id))
        except sqlite3.IntegrityError as error:
            self._raise_integrity(error)
        result = self.find_catalog(resource, item_id)
        assert result is not None
        return result

    def delete_catalog(self, resource: str, item_id: str) -> None:
        table, _ = self._catalog(resource)
        try:
            self.db.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
        except sqlite3.IntegrityError as error:
            raise ConflictError("O registro está em uso e não pode ser excluído.") from error

    def find_class_with_skills(self, item_id: str) -> dict[str, Any] | None:
        result = self.find_catalog("classes", item_id)
        if result:
            result["skillIds"] = [row["id"] for row in self.db.fetchall("SELECT id FROM skills WHERE class_id = ?", (item_id,))]
        return result

    def find_race_with_skills(self, item_id: str) -> dict[str, Any] | None:
        result = self.find_catalog("races", item_id)
        if result:
            result["skillIds"] = [row["id"] for row in self.db.fetchall("SELECT id FROM skills WHERE race_id = ?", (item_id,))]
        return result

    # Personagens
    def create_character(self, character: Character) -> Character:
        character.id = str(uuid4())
        character.created_at = datetime.now(UTC).isoformat()
        with self.db.transaction():
            self.db.execute(
                """
                INSERT INTO characters (
                    id, player_id, class_id, race_id, name, level, experience, health, max_health,
                    energy, max_energy, strength, defense, agility, intelligence, vitality, charisma,
                    attribute_points, coins, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._character_values(character),
            )
            for skill_id in character.skill_ids:
                self.db.execute(
                    "INSERT OR IGNORE INTO character_skills (character_id, skill_id) VALUES (?, ?)",
                    (character.id, skill_id),
                )
        result = self.find_character(character.id)
        assert result is not None
        return result

    def find_character(self, character_id: str) -> Character | None:
        return self._map_character(self.db.fetchone(self._character_query("WHERE c.id = ?"), (character_id,)))

    def list_characters_by_player(self, player_id: str) -> list[Character]:
        return [
            self._map_character(row)
            for row in self.db.fetchall(self._character_query("WHERE c.player_id = ? ORDER BY c.created_at DESC"), (player_id,))
        ]

    def list_all_characters(self) -> list[Character]:
        return [self._map_character(row) for row in self.db.fetchall(self._character_query("ORDER BY c.created_at DESC"))]

    def save_character(self, character: Character) -> Character:
        self._save_character(character)
        result = self.find_character(character.id or "")
        assert result is not None
        return result

    # Missões
    def list_available_missions(self, character_id: str) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            """
            SELECT m.* FROM missions m
            WHERE m.status = 'DISPONIVEL'
              AND NOT EXISTS (
                SELECT 1 FROM character_missions cm
                WHERE cm.mission_id = m.id AND cm.character_id = ?
              )
            ORDER BY m.min_level, m.title
            """,
            (character_id,),
        )
        return [self._map_catalog("missions", row) for row in rows]

    def find_mission(self, mission_id: str) -> dict[str, Any] | None:
        return self.find_catalog("missions", mission_id)

    def accept_mission(self, character_id: str, mission_id: str) -> MissionProgress:
        mission = self.find_mission(mission_id)
        assert mission is not None
        progress_id = str(uuid4())
        try:
            self.db.execute(
                """
                INSERT INTO character_missions (id, character_id, mission_id, status, progress, target, accepted_at)
                VALUES (?, ?, ?, 'ACEITA', 0, ?, ?)
                """,
                (progress_id, character_id, mission_id, mission["target"], datetime.now(UTC).isoformat()),
            )
        except sqlite3.IntegrityError as error:
            raise ConflictError("Esta missão já foi aceita pelo personagem.") from error
        result = self.find_mission_progress(progress_id)
        assert result is not None
        return result

    def find_mission_progress(self, progress_id: str) -> MissionProgress | None:
        row = self.db.fetchone(
            """
            SELECT cm.*, m.title, m.objective FROM character_missions cm
            JOIN missions m ON m.id = cm.mission_id WHERE cm.id = ?
            """,
            (progress_id,),
        )
        return self._map_progress(row) if row else None

    def list_character_missions(self, character_id: str) -> list[MissionProgress]:
        return [
            self._map_progress(row)
            for row in self.db.fetchall(
                """
                SELECT cm.*, m.title, m.objective FROM character_missions cm
                JOIN missions m ON m.id = cm.mission_id
                WHERE cm.character_id = ? ORDER BY cm.accepted_at DESC
                """,
                (character_id,),
            )
        ]

    def save_mission_progress(self, progress: MissionProgress) -> MissionProgress:
        self.db.execute(
            "UPDATE character_missions SET status = ?, progress = ?, completed_at = ? WHERE id = ?",
            (progress.status.value, progress.progress, progress.completed_at, progress.id),
        )
        result = self.find_mission_progress(progress.id)
        assert result is not None
        return result

    def complete_mission(self, progress: MissionProgress, character: Character, mission: dict[str, Any]) -> None:
        progress.completed_at = datetime.now(UTC).isoformat()
        with self.db.transaction():
            self.db.execute(
                "UPDATE character_missions SET status = ?, progress = ?, completed_at = ? WHERE id = ?",
                (progress.status.value, progress.progress, progress.completed_at, progress.id),
            )
            self._save_character(character)
            if mission["rewardItemId"] and mission["rewardItemQuantity"] > 0:
                self._add_inventory(character.id or "", mission["rewardItemId"], mission["rewardItemQuantity"])

    # Inventário
    def list_inventory(self, character_id: str) -> list[dict[str, Any]]:
        return [self._map_inventory(row) for row in self.db.fetchall(self._inventory_query() + " ORDER BY inv.equipped DESC, i.name", (character_id,))]

    def find_inventory_item(self, character_id: str, item_id: str) -> dict[str, Any] | None:
        row = self.db.fetchone(self._inventory_query("AND inv.item_id = ?"), (character_id, item_id))
        return self._map_inventory(row) if row else None

    def add_inventory_item(self, character_id: str, item_id: str, quantity: int) -> dict[str, Any]:
        self._add_inventory(character_id, item_id, quantity)
        result = self.find_inventory_item(character_id, item_id)
        assert result is not None
        return result

    def remove_inventory_item(self, character_id: str, item_id: str, quantity: int) -> dict[str, Any] | None:
        entry = self.find_inventory_item(character_id, item_id)
        if not entry:
            raise NotFoundError("Item do inventário")
        if entry["quantity"] < quantity:
            raise ConflictError("Quantidade insuficiente no inventário.")
        remaining = entry["quantity"] - quantity
        if remaining == 0:
            self.db.execute("DELETE FROM inventory WHERE character_id = ? AND item_id = ?", (character_id, item_id))
            return None
        self.db.execute(
            "UPDATE inventory SET quantity = ? WHERE character_id = ? AND item_id = ?",
            (remaining, character_id, item_id),
        )
        return self.find_inventory_item(character_id, item_id)

    def equip_inventory_item(self, character_id: str, item_id: str, equipped: bool) -> dict[str, Any]:
        cursor = self.db.execute(
            "UPDATE inventory SET equipped = ? WHERE character_id = ? AND item_id = ?",
            (int(equipped), character_id, item_id),
        )
        if cursor.rowcount == 0:
            raise NotFoundError("Item do inventário")
        result = self.find_inventory_item(character_id, item_id)
        assert result is not None
        return result

    # Combates
    def create_combat(self, combat: dict[str, Any], character: Character) -> dict[str, Any]:
        with self.db.transaction():
            self.db.execute(
                """
                INSERT INTO combats (
                    id, character_id, enemy_id, status, enemy_health, enemy_max_health, started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    combat["id"], combat["characterId"], combat["enemyId"], combat["status"],
                    combat["enemyHealth"], combat["enemyMaxHealth"], combat["startedAt"], combat["finishedAt"],
                ),
            )
            self._save_character(character)
        result = self.find_combat(combat["id"])
        assert result is not None
        return result

    def find_combat(self, combat_id: str) -> dict[str, Any] | None:
        row = self.db.fetchone(
            "SELECT c.*, e.name AS enemy_name FROM combats c JOIN enemies e ON e.id = c.enemy_id WHERE c.id = ?",
            (combat_id,),
        )
        if not row:
            return None
        turns = [
            {
                "actor": item["actor"], "action": item["action"], "damage": item["damage"],
                "enemyDamage": item["enemy_damage"],
                "playerRoll": item["player_roll"],
                "playerHitChance": item["player_hit_chance"],
                "playerHit": bool(item["player_hit"]) if item["player_hit"] is not None else None,
                "enemyRoll": item["enemy_roll"],
                "enemyHitChance": item["enemy_hit_chance"],
                "enemyHit": bool(item["enemy_hit"]) if item["enemy_hit"] is not None else None,
                "occurredAt": item["occurred_at"],
            }
            for item in self.db.fetchall(
                "SELECT * FROM combat_turns WHERE combat_id = ? ORDER BY id", (combat_id,)
            )
        ]
        return self._map_combat(row, turns)

    def save_combat_turn(
        self, combat: dict[str, Any], turn: dict[str, Any], character: Character
    ) -> dict[str, Any]:
        with self.db.transaction():
            self.db.execute(
                "UPDATE combats SET status = ?, enemy_health = ?, finished_at = ? WHERE id = ?",
                (combat["status"], combat["enemyHealth"], combat["finishedAt"], combat["id"]),
            )
            self.db.execute(
                """
                INSERT INTO combat_turns (
                    combat_id, actor, action, damage, enemy_damage, player_roll,
                    player_hit_chance, player_hit, enemy_roll, enemy_hit_chance,
                    enemy_hit, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    combat["id"], turn["actor"], turn["action"], turn["damage"],
                    turn.get("enemyDamage", 0), turn.get("playerRoll"),
                    turn.get("playerHitChance"),
                    int(turn["playerHit"]) if turn.get("playerHit") is not None else None,
                    turn.get("enemyRoll"), turn.get("enemyHitChance"),
                    int(turn["enemyHit"]) if turn.get("enemyHit") is not None else None,
                    turn["occurredAt"],
                ),
            )
            self._save_character(character)
            if turn.get("rewardItemId"):
                self._add_inventory(character.id or "", turn["rewardItemId"], 1)
        result = self.find_combat(combat["id"])
        assert result is not None
        return result

    def list_character_combats(self, character_id: str) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT id FROM combats WHERE character_id = ? ORDER BY started_at DESC",
            (character_id,),
        )
        return [combat for row in rows if (combat := self.find_combat(row["id"])) is not None]

    # Histórico (assinante do Observer)
    def add_history(self, event: DomainEvent) -> None:
        self.db.execute(
            """
            INSERT INTO history (event_type, actor_id, character_id, description, data, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event.type, event.actor_id, event.character_id, event.description, json.dumps(event.data), event.occurred_at),
        )

    def list_history(self, character_id: str) -> list[dict[str, Any]]:
        return [
            {
                "id": row["id"], "type": row["event_type"], "actorId": row["actor_id"],
                "characterId": row["character_id"], "description": row["description"],
                "data": json.loads(row["data"]), "occurredAt": row["occurred_at"],
            }
            for row in self.db.fetchall(
                "SELECT * FROM history WHERE character_id = ? ORDER BY occurred_at DESC, id DESC",
                (character_id,),
            )
        ]

    # Conversores e operações internas
    @staticmethod
    def _map_user(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {
            "id": row["id"], "name": row["name"], "email": row["email"],
            "passwordHash": row["password_hash"], "role": row["role"], "createdAt": row["created_at"],
        }

    @staticmethod
    def _catalog(resource: str) -> tuple[str, str]:
        if resource not in CATALOG_TABLES:
            raise NotFoundError("Catálogo")
        return CATALOG_TABLES[resource]

    def _map_catalog(self, resource: str, row: sqlite3.Row) -> dict[str, Any]:
        if resource == "classes":
            return {
                "id": row["id"], "name": row["name"], "description": row["description"],
                "attributes": {name: row[name] for name in ATTRIBUTE_FIELDS}, "baseHealth": row["base_health"],
                "baseEnergy": row["base_energy"],
            }
        if resource == "races":
            return {
                "id": row["id"], "name": row["name"], "description": row["description"],
                "modifiers": {name: row[name] for name in ATTRIBUTE_FIELDS},
            }
        if resource == "skills":
            return {
                "id": row["id"], "name": row["name"], "description": row["description"],
                "type": row["type"], "energyCost": row["energy_cost"], "damage": row["damage"],
                "effect": row["effect"], "cooldown": row["cooldown"], "minLevel": row["min_level"],
                "classId": row["class_id"], "raceId": row["race_id"],
            }
        if resource == "items":
            return {
                "id": row["id"], "name": row["name"], "type": row["type"],
                "description": row["description"], "rarity": row["rarity"], "value": row["value"],
                "effectHealth": row["effect_health"], "effectEnergy": row["effect_energy"],
                "attackBonus": row["attack_bonus"], "defenseBonus": row["defense_bonus"],
                "requiredClassId": row["required_class_id"], "minLevel": row["min_level"],
            }
        if resource == "missions":
            return {
                "id": row["id"], "title": row["title"], "description": row["description"],
                "objective": row["objective"], "minLevel": row["min_level"], "status": row["status"],
                "target": row["target"], "rewardExperience": row["reward_experience"],
                "rewardCoins": row["reward_coins"], "rewardItemId": row["reward_item_id"],
                "rewardItemQuantity": row["reward_item_quantity"],
            }
        return {
            "id": row["id"], "name": row["name"], "type": row["type"], "level": row["level"],
            "health": row["health"], "strength": row["strength"], "defense": row["defense"],
            "agility": row["agility"], "rewardExperience": row["reward_experience"],
            "rewardCoins": row["reward_coins"], "rewardItemId": row["reward_item_id"],
        }

    def _normalize_catalog(self, resource: str, data: dict[str, Any]) -> dict[str, Any]:
        if resource == "classes":
            attributes = Attributes.from_dict(data.get("attributes")).to_dict()
            return {
                "name": self._text(data.get("name"), "nome"),
                "description": str(data.get("description", "")),
                **attributes,
                "base_health": self._positive(data.get("baseHealth", 50), "vida base"),
                "base_energy": self._positive(data.get("baseEnergy", 20), "energia base"),
            }
        if resource == "races":
            modifiers = Attributes.from_dict(data.get("modifiers")).to_dict()
            return {
                "name": self._text(data.get("name"), "nome"),
                "description": str(data.get("description", "")),
                **modifiers,
            }
        if resource == "skills":
            return {
                "name": self._text(data.get("name"), "nome"),
                "description": str(data.get("description", "")),
                "type": str(data.get("type", "MAGICA")).upper(),
                "energy_cost": self._non_negative(data.get("energyCost", 0)),
                "damage": self._non_negative(data.get("damage", 0)),
                "effect": str(data.get("effect", "")),
                "cooldown": self._non_negative(data.get("cooldown", 0)),
                "min_level": self._positive(data.get("minLevel", 1), "nível mínimo"),
                "class_id": data.get("classId"),
                "race_id": data.get("raceId"),
            }
        if resource == "items":
            return {
                "name": self._text(data.get("name"), "nome"),
                "type": self._text(data.get("type"), "tipo").upper(),
                "description": str(data.get("description", "")),
                "rarity": str(data.get("rarity", "COMUM")).upper(),
                "value": self._non_negative(data.get("value", 0)),
                "effect_health": self._integer(data.get("effectHealth", 0)),
                "effect_energy": self._integer(data.get("effectEnergy", 0)),
                "attack_bonus": self._integer(data.get("attackBonus", 0)),
                "defense_bonus": self._integer(data.get("defenseBonus", 0)),
                "required_class_id": data.get("requiredClassId"),
                "min_level": self._positive(data.get("minLevel", 1), "nível mínimo"),
            }
        if resource == "missions":
            return {
                "title": self._text(data.get("title"), "título"),
                "description": str(data.get("description", "")),
                "objective": self._text(data.get("objective"), "objetivo"),
                "min_level": self._positive(data.get("minLevel", 1), "nível mínimo"),
                "status": str(data.get("status", "DISPONIVEL")).upper(),
                "target": self._positive(data.get("target", 1), "meta"),
                "reward_experience": self._non_negative(data.get("rewardExperience", 0)),
                "reward_coins": self._non_negative(data.get("rewardCoins", 0)),
                "reward_item_id": data.get("rewardItemId"),
                "reward_item_quantity": self._non_negative(data.get("rewardItemQuantity", 0)),
            }
        return {
            "name": self._text(data.get("name"), "nome"),
            "type": str(data.get("type", "MONSTRO")).upper(),
            "level": self._positive(data.get("level", 1), "nível"),
            "health": self._positive(data.get("health", 20), "vida"),
            "strength": self._non_negative(data.get("strength", 5)),
            "defense": self._non_negative(data.get("defense", 1)),
            "agility": self._non_negative(data.get("agility", 1)),
            "reward_experience": self._non_negative(data.get("rewardExperience", 0)),
            "reward_coins": self._non_negative(data.get("rewardCoins", 0)),
            "reward_item_id": data.get("rewardItemId"),
        }

    @staticmethod
    def _character_query(suffix: str = "") -> str:
        return f"""
            SELECT c.*, cl.name AS class_name, r.name AS race_name,
                COALESCE((SELECT SUM(i.attack_bonus) FROM inventory inv JOIN items i ON i.id = inv.item_id
                    WHERE inv.character_id = c.id AND inv.equipped = 1), 0) AS equipment_attack,
                COALESCE((SELECT SUM(i.defense_bonus) FROM inventory inv JOIN items i ON i.id = inv.item_id
                    WHERE inv.character_id = c.id AND inv.equipped = 1), 0) AS equipment_defense
            FROM characters c JOIN character_classes cl ON cl.id = c.class_id JOIN races r ON r.id = c.race_id {suffix}
        """

    def _map_character(self, row: sqlite3.Row | None) -> Character | None:
        if not row:
            return None
        skills = [
            self._map_catalog("skills", item)
            for item in self.db.fetchall(
                """
                SELECT s.* FROM skills s
                WHERE (s.class_id IS NULL AND s.race_id IS NULL)
                    OR s.class_id = ? OR s.race_id = ? OR EXISTS (
                    SELECT 1 FROM character_skills cs
                    WHERE cs.skill_id = s.id AND cs.character_id = ?
                )
                ORDER BY s.min_level, s.name
                """,
                (row["class_id"], row["race_id"], row["id"]),
            )
        ]
        return Character(
            id=row["id"], player_id=row["player_id"], name=row["name"], class_id=row["class_id"],
            class_name=row["class_name"], race_id=row["race_id"], race_name=row["race_name"],
            level=row["level"], experience=row["experience"], health=row["health"], max_health=row["max_health"],
            energy=row["energy"], max_energy=row["max_energy"],
            attributes=Attributes.from_dict({name: row[name] for name in ATTRIBUTE_FIELDS}),
            attribute_points=row["attribute_points"], coins=row["coins"], status=row["status"],
            skill_ids=[skill["id"] for skill in skills], skills=skills,
            equipment_bonuses={"attack": row["equipment_attack"], "defense": row["equipment_defense"]},
            created_at=row["created_at"],
        )

    @staticmethod
    def _character_values(character: Character) -> tuple[Any, ...]:
        return (
            character.id, character.player_id, character.class_id, character.race_id, character.name,
            character.level, character.experience, character.health, character.max_health,
            character.energy, character.max_energy,
            *(getattr(character.attributes, name) for name in ATTRIBUTE_FIELDS),
            character.attribute_points, character.coins, character.status.value, character.created_at,
        )

    def _save_character(self, character: Character) -> None:
        self.db.execute(
            """
            UPDATE characters SET level = ?, experience = ?, health = ?, max_health = ?, energy = ?,
                max_energy = ?, strength = ?, defense = ?, agility = ?, intelligence = ?, vitality = ?,
                charisma = ?, attribute_points = ?, coins = ?, status = ? WHERE id = ?
            """,
            (
                character.level, character.experience, character.health, character.max_health,
                character.energy, character.max_energy,
                *(getattr(character.attributes, name) for name in ATTRIBUTE_FIELDS),
                character.attribute_points, character.coins, character.status.value, character.id,
            ),
        )

    @staticmethod
    def _map_progress(row: sqlite3.Row) -> MissionProgress:
        return MissionProgress(
            id=row["id"], character_id=row["character_id"], mission_id=row["mission_id"],
            status=row["status"], progress=row["progress"], target=row["target"],
            accepted_at=row["accepted_at"], completed_at=row["completed_at"],
            title=row["title"], objective=row["objective"],
        )

    @staticmethod
    def _inventory_query(extra: str = "") -> str:
        return f"""
            SELECT inv.character_id, inv.item_id, inv.quantity, inv.equipped,
                i.name, i.type, i.description, i.rarity, i.value, i.effect_health, i.effect_energy,
                i.attack_bonus, i.defense_bonus, i.required_class_id, i.min_level
            FROM inventory inv JOIN items i ON i.id = inv.item_id
            WHERE inv.character_id = ? {extra}
        """

    @staticmethod
    def _map_inventory(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "characterId": row["character_id"], "itemId": row["item_id"], "quantity": row["quantity"],
            "equipped": bool(row["equipped"]), "name": row["name"], "type": row["type"],
            "description": row["description"], "rarity": row["rarity"], "value": row["value"],
            "effectHealth": row["effect_health"], "effectEnergy": row["effect_energy"],
            "attackBonus": row["attack_bonus"], "defenseBonus": row["defense_bonus"],
            "requiredClassId": row["required_class_id"], "minLevel": row["min_level"],
        }

    def _add_inventory(self, character_id: str, item_id: str, quantity: int) -> None:
        self.db.execute(
            """
            INSERT INTO inventory (character_id, item_id, quantity, equipped) VALUES (?, ?, ?, 0)
            ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (character_id, item_id, quantity),
        )

    @staticmethod
    def _map_combat(row: sqlite3.Row, turns: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return {
            "id": row["id"], "characterId": row["character_id"], "enemyId": row["enemy_id"],
            "enemyName": row["enemy_name"], "status": row["status"], "enemyHealth": row["enemy_health"],
            "enemyMaxHealth": row["enemy_max_health"], "startedAt": row["started_at"],
            "finishedAt": row["finished_at"], "turns": turns or [],
        }

    @staticmethod
    def _text(value: Any, label: str) -> str:
        result = str(value or "").strip()
        if not result:
            raise ValidationError(f"O campo {label} é obrigatório.")
        return result

    @staticmethod
    def _integer(value: Any) -> int:
        if isinstance(value, bool):
            raise ValidationError("Os valores numéricos devem ser inteiros.")
        try:
            result = int(value)
        except (TypeError, ValueError) as error:
            raise ValidationError("Os valores numéricos devem ser inteiros.") from error
        if isinstance(value, float) and not value.is_integer():
            raise ValidationError("Os valores numéricos devem ser inteiros.")
        return result

    @classmethod
    def _non_negative(cls, value: Any) -> int:
        result = cls._integer(value)
        if result < 0:
            raise ValidationError("O valor não pode ser negativo.")
        return result

    @classmethod
    def _positive(cls, value: Any, label: str) -> int:
        result = cls._integer(value)
        if result <= 0:
            raise ValidationError(f"O campo {label} deve ser positivo.")
        return result

    @staticmethod
    def _raise_integrity(error: sqlite3.IntegrityError) -> None:
        message = str(error).upper()
        if "UNIQUE" in message:
            raise ConflictError("Já existe um registro com este nome.") from error
        if "FOREIGN KEY" in message:
            raise ValidationError("Uma referência informada não existe.") from error
        raise error
