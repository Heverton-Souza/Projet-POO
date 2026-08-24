import re
from datetime import UTC, datetime, timedelta
from typing import Any

from app.domain.enums import UserRole
from app.domain.errors import AuthenticationError, ConflictError, ValidationError

from .ports import IdGenerator, PasswordHasher, TokenService, UserRepository


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
        id_generator: IdGenerator,
        session_hours: int = 12,
    ) -> None:
        self.users = users
        self.password_hasher = password_hasher
        self.token_service = token_service
        self.id_generator = id_generator
        self.session_hours = session_hours

    def register(self, name: str, email: str, password: str) -> dict[str, Any]:
        name = name.strip()
        email = email.strip().lower()
        if not name:
            raise ValidationError("O nome é obrigatório.")
        if not re.fullmatch(r"\S+@\S+\.\S+", email):
            raise ValidationError("Informe um e-mail válido.")
        if len(password) < 8:
            raise ValidationError("A senha deve possuir ao menos 8 caracteres.")
        if self.users.find_user_by_email(email):
            raise ConflictError("Já existe uma conta com este e-mail.")
        user = self.users.create_user(
            {
                "id": self.id_generator.generate(),
                "name": name,
                "email": email,
                "passwordHash": self.password_hasher.hash(password),
                "role": UserRole.PLAYER.value,
                "createdAt": datetime.now(UTC).isoformat(),
            }
        )
        return self.public_user(user)

    def login(self, email: str, password: str) -> dict[str, Any]:
        user = self.users.find_user_by_email(email.strip().lower())
        if not user or not self.password_hasher.verify(password, user["passwordHash"]):
            raise AuthenticationError("E-mail ou senha inválidos.")
        token = self.token_service.generate()
        expires_at = (datetime.now(UTC) + timedelta(hours=self.session_hours)).isoformat()
        self.users.create_session(
            {
                "id": self.id_generator.generate(),
                "userId": user["id"],
                "tokenHash": self.token_service.hash(token),
                "expiresAt": expires_at,
            }
        )
        return {"token": token, "expiresAt": expires_at, "user": self.public_user(user)}

    def authenticate(self, token: str | None) -> dict[str, Any]:
        if not token:
            raise AuthenticationError()
        session = self.users.find_valid_session(self.token_service.hash(token), datetime.now(UTC).isoformat())
        if not session:
            raise AuthenticationError("Sessão inválida ou expirada.")
        user = self.users.find_user(session["userId"])
        if not user:
            raise AuthenticationError()
        return self.public_user(user)

    def logout(self, token: str | None) -> None:
        if token:
            self.users.delete_session(self.token_service.hash(token))

    @staticmethod
    def public_user(user: dict[str, Any]) -> dict[str, Any]:
        return {key: user[key] for key in ("id", "name", "email", "role", "createdAt")}
