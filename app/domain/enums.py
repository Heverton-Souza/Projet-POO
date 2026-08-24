from enum import StrEnum


class UserRole(StrEnum):
    PLAYER = "JOGADOR"
    GAME_MASTER = "MESTRE"
    ADMIN = "ADMINISTRADOR"


class CharacterStatus(StrEnum):
    ACTIVE = "ATIVO"
    INACTIVE = "INATIVO"
    DEFEATED = "DERROTADO"
    ON_MISSION = "EM_MISSAO"
    IN_COMBAT = "EM_COMBATE"


class MissionStatus(StrEnum):
    AVAILABLE = "DISPONIVEL"
    ACCEPTED = "ACEITA"
    IN_PROGRESS = "EM_ANDAMENTO"
    COMPLETED = "CONCLUIDA"
    CANCELLED = "CANCELADA"


class CombatStatus(StrEnum):
    IN_PROGRESS = "EM_ANDAMENTO"
    VICTORY = "VITORIA"
    DEFEAT = "DERROTA"
    FLED = "FUGA"


class ItemType(StrEnum):
    WEAPON = "ARMA"
    ARMOR = "ARMADURA"
    POTION = "POCAO"
    ACCESSORY = "ACESSORIO"
    QUEST = "MISSAO"


ADMIN_ROLES = {UserRole.GAME_MASTER, UserRole.ADMIN}

