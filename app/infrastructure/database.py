import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any, Iterator


class Database:
    def __init__(self, filename: str) -> None:
        if filename != ":memory:":
            Path(filename).resolve().parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(filename, check_same_thread=False, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.lock = RLock()
        self.execute("PRAGMA foreign_keys = ON")
        self.execute("PRAGMA journal_mode = WAL")

    def execute(self, sql: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self.lock:
            return self.connection.execute(sql, parameters)

    def fetchone(self, sql: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self.lock:
            return self.connection.execute(sql, parameters).fetchone()

    def fetchall(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.lock:
            return self.connection.execute(sql, parameters).fetchall()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self.lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.connection.execute("COMMIT")
            except Exception:
                self.connection.execute("ROLLBACK")
                raise

    def migrate(self) -> None:
        with self.lock:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('JOGADOR','MESTRE','ADMINISTRADOR')),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS character_classes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    strength INTEGER NOT NULL DEFAULT 0,
                    defense INTEGER NOT NULL DEFAULT 0,
                    agility INTEGER NOT NULL DEFAULT 0,
                    intelligence INTEGER NOT NULL DEFAULT 0,
                    vitality INTEGER NOT NULL DEFAULT 0,
                    charisma INTEGER NOT NULL DEFAULT 0,
                    base_health INTEGER NOT NULL DEFAULT 50,
                    base_energy INTEGER NOT NULL DEFAULT 20,
                    created_by TEXT REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS races (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    strength INTEGER NOT NULL DEFAULT 0,
                    defense INTEGER NOT NULL DEFAULT 0,
                    agility INTEGER NOT NULL DEFAULT 0,
                    intelligence INTEGER NOT NULL DEFAULT 0,
                    vitality INTEGER NOT NULL DEFAULT 0,
                    charisma INTEGER NOT NULL DEFAULT 0,
                    created_by TEXT REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS skills (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    type TEXT NOT NULL DEFAULT 'MAGICA',
                    energy_cost INTEGER NOT NULL DEFAULT 0,
                    damage INTEGER NOT NULL DEFAULT 0,
                    effect TEXT NOT NULL DEFAULT '',
                    cooldown INTEGER NOT NULL DEFAULT 0,
                    min_level INTEGER NOT NULL DEFAULT 1,
                    class_id TEXT REFERENCES character_classes(id) ON DELETE SET NULL,
                    race_id TEXT REFERENCES races(id) ON DELETE SET NULL,
                    created_by TEXT REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    rarity TEXT NOT NULL DEFAULT 'COMUM',
                    value INTEGER NOT NULL DEFAULT 0,
                    effect_health INTEGER NOT NULL DEFAULT 0,
                    effect_energy INTEGER NOT NULL DEFAULT 0,
                    attack_bonus INTEGER NOT NULL DEFAULT 0,
                    defense_bonus INTEGER NOT NULL DEFAULT 0,
                    required_class_id TEXT REFERENCES character_classes(id) ON DELETE SET NULL,
                    min_level INTEGER NOT NULL DEFAULT 1,
                    created_by TEXT REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS characters (
                    id TEXT PRIMARY KEY,
                    player_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    class_id TEXT NOT NULL REFERENCES character_classes(id),
                    race_id TEXT NOT NULL REFERENCES races(id),
                    name TEXT NOT NULL,
                    level INTEGER NOT NULL DEFAULT 1,
                    experience INTEGER NOT NULL DEFAULT 0,
                    health INTEGER NOT NULL,
                    max_health INTEGER NOT NULL,
                    energy INTEGER NOT NULL,
                    max_energy INTEGER NOT NULL,
                    strength INTEGER NOT NULL DEFAULT 0,
                    defense INTEGER NOT NULL DEFAULT 0,
                    agility INTEGER NOT NULL DEFAULT 0,
                    intelligence INTEGER NOT NULL DEFAULT 0,
                    vitality INTEGER NOT NULL DEFAULT 0,
                    charisma INTEGER NOT NULL DEFAULT 0,
                    attribute_points INTEGER NOT NULL DEFAULT 0,
                    coins INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS character_skills (
                    character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
                    skill_id TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
                    PRIMARY KEY (character_id, skill_id)
                );

                CREATE TABLE IF NOT EXISTS inventory (
                    character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
                    item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
                    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 0),
                    equipped INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (character_id, item_id)
                );

                CREATE TABLE IF NOT EXISTS missions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    objective TEXT NOT NULL,
                    min_level INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'DISPONIVEL',
                    target INTEGER NOT NULL DEFAULT 1,
                    reward_experience INTEGER NOT NULL DEFAULT 0,
                    reward_coins INTEGER NOT NULL DEFAULT 0,
                    reward_item_id TEXT REFERENCES items(id) ON DELETE SET NULL,
                    reward_item_quantity INTEGER NOT NULL DEFAULT 0,
                    created_by TEXT REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS character_missions (
                    id TEXT PRIMARY KEY,
                    character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
                    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    target INTEGER NOT NULL DEFAULT 1,
                    accepted_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE (character_id, mission_id)
                );

                CREATE TABLE IF NOT EXISTS enemies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL DEFAULT 'MONSTRO',
                    level INTEGER NOT NULL DEFAULT 1,
                    health INTEGER NOT NULL DEFAULT 20,
                    strength INTEGER NOT NULL DEFAULT 5,
                    defense INTEGER NOT NULL DEFAULT 1,
                    agility INTEGER NOT NULL DEFAULT 1,
                    reward_experience INTEGER NOT NULL DEFAULT 0,
                    reward_coins INTEGER NOT NULL DEFAULT 0,
                    reward_item_id TEXT REFERENCES items(id) ON DELETE SET NULL,
                    created_by TEXT REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS combats (
                    id TEXT PRIMARY KEY,
                    character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
                    enemy_id TEXT NOT NULL REFERENCES enemies(id),
                    status TEXT NOT NULL,
                    enemy_health INTEGER NOT NULL,
                    enemy_max_health INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT
                );

                CREATE TABLE IF NOT EXISTS combat_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    combat_id TEXT NOT NULL REFERENCES combats(id) ON DELETE CASCADE,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    damage INTEGER NOT NULL DEFAULT 0,
                    enemy_damage INTEGER NOT NULL DEFAULT 0,
                    player_roll INTEGER,
                    player_hit_chance INTEGER,
                    player_hit INTEGER,
                    enemy_roll INTEGER,
                    enemy_hit_chance INTEGER,
                    enemy_hit INTEGER,
                    occurred_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    actor_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                    character_id TEXT REFERENCES characters(id) ON DELETE CASCADE,
                    description TEXT NOT NULL,
                    data TEXT NOT NULL DEFAULT '{}',
                    occurred_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash, expires_at);
                CREATE INDEX IF NOT EXISTS idx_characters_player ON characters(player_id);
                CREATE INDEX IF NOT EXISTS idx_character_missions_character ON character_missions(character_id);
                CREATE INDEX IF NOT EXISTS idx_history_character ON history(character_id, occurred_at);
                """
            )
            self._ensure_columns(
                "combat_turns",
                {
                    "player_roll": "INTEGER",
                    "player_hit_chance": "INTEGER",
                    "player_hit": "INTEGER",
                    "enemy_roll": "INTEGER",
                    "enemy_hit_chance": "INTEGER",
                    "enemy_hit": "INTEGER",
                },
            )

    def _ensure_columns(self, table: str, columns: dict[str, str]) -> None:
        existing = {
            row["name"] for row in self.connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, definition in columns.items():
            if name not in existing:
                self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def close(self) -> None:
        with self.lock:
            self.connection.close()
