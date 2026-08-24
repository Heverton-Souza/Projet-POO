import hashlib
import secrets
from uuid import uuid4

from app.application.ports import IdGenerator, PasswordHasher, TokenService


class ScryptPasswordHasher(PasswordHasher):
    def hash(self, plain_text: str) -> str:
        salt = secrets.token_bytes(16)
        derived = hashlib.scrypt(plain_text.encode(), salt=salt, n=2**14, r=8, p=1, dklen=64)
        return f"{salt.hex()}:{derived.hex()}"

    def verify(self, plain_text: str, encoded: str) -> bool:
        try:
            salt_hex, expected_hex = encoded.split(":", 1)
            expected = bytes.fromhex(expected_hex)
            # Formato Python atual: o salt hexadecimal volta a ser bytes.
            current = hashlib.scrypt(
                plain_text.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=len(expected)
            )
            if secrets.compare_digest(expected, current):
                return True

            # Compatibilidade com a versão Node: scryptSync recebeu o texto
            # hexadecimal como salt, não os bytes que ele representa.
            legacy = hashlib.scrypt(
                plain_text.encode(), salt=salt_hex.encode(), n=2**14, r=8, p=1, dklen=len(expected)
            )
            return secrets.compare_digest(expected, legacy)
        except (ValueError, TypeError):
            return False


class SecureTokenService(TokenService):
    def generate(self) -> str:
        return secrets.token_urlsafe(32)

    def hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()


class UuidGenerator(IdGenerator):
    def generate(self) -> str:
        return str(uuid4())
