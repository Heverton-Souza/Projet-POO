from typing import Any

from app.domain.entities import Character
from app.domain.enums import ADMIN_ROLES, UserRole
from app.domain.errors import AuthorizationError


class AuthorizationPolicy:
    def require_game_master(self, user: dict[str, Any]) -> None:
        if UserRole(user["role"]) not in ADMIN_ROLES:
            raise AuthorizationError("Apenas mestres ou administradores podem gerenciar o jogo.")

    def require_administrator(self, user: dict[str, Any]) -> None:
        if UserRole(user["role"]) is not UserRole.ADMIN:
            raise AuthorizationError("Apenas administradores podem gerenciar permissões.")

    def require_character_owner(self, user: dict[str, Any], character: Character) -> None:
        if character.player_id != user["id"] and UserRole(user["role"]) not in ADMIN_ROLES:
            raise AuthorizationError("Este personagem pertence a outro jogador.")

