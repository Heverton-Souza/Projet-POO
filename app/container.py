from dataclasses import dataclass

from app.application.auth_service import AuthService
from app.application.authorization import AuthorizationPolicy
from app.application.ports import DiceRoller
from app.application.game_services import (
    AdminService,
    CharacterService,
    CombatService,
    HistoryService,
    InventoryService,
    MissionService,
)
from app.infrastructure.database import Database
from app.infrastructure.dice import D100DiceRoller
from app.infrastructure.event_publisher import InMemoryEventPublisher
from app.infrastructure.repositories import SqliteRepository
from app.infrastructure.security import ScryptPasswordHasher, SecureTokenService, UuidGenerator
from app.infrastructure.seed import seed_database

from .config import Config


@dataclass
class Services:
    auth: AuthService
    characters: CharacterService
    missions: MissionService
    inventory: InventoryService
    combats: CombatService
    admin: AdminService
    history: HistoryService


@dataclass
class Container:
    database: Database
    repository: SqliteRepository
    services: Services

    def close(self) -> None:
        self.database.close()


def create_container(config: Config, dice_roller: DiceRoller | None = None) -> Container:
    database = Database(config.database_path)
    database.migrate()
    repository = SqliteRepository(database)
    password_hasher = ScryptPasswordHasher()
    token_service = SecureTokenService()
    id_generator = UuidGenerator()
    authorization = AuthorizationPolicy()
    events = InMemoryEventPublisher()
    active_dice_roller = dice_roller or D100DiceRoller()
    events.subscribe("*", repository.add_history)

    if config.seed:
        seed_database(repository, password_hasher, id_generator, config)

    services = Services(
        auth=AuthService(repository, password_hasher, token_service, id_generator, config.session_hours),
        characters=CharacterService(repository, repository, events, authorization),
        missions=MissionService(repository, repository, events, authorization),
        inventory=InventoryService(repository, repository, repository, events, authorization),
        combats=CombatService(
            repository,
            repository,
            repository,
            events,
            authorization,
            id_generator,
            active_dice_roller,
        ),
        admin=AdminService(repository, repository, repository, authorization),
        history=HistoryService(repository, repository, authorization),
    )
    return Container(database, repository, services)
