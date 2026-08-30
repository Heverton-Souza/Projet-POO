from dataclasses import dataclass
from typing import Any


@dataclass
class User:
    id: str
    name: str
    email: str
    password_hash: str
    role: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "passwordHash": self.password_hash,
            "role": self.role,
            "createdAt": self.created_at,
        }
