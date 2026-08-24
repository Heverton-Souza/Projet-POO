import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(filename: str = ".env") -> None:
    path = Path(filename)
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Config:
    host: str = "127.0.0.1"
    port: int = 3000
    database_path: str = "./data/rpg.sqlite"
    master_name: str = "Mestre do Jogo"
    master_email: str = "mestre@rpg.local"
    master_password: str = "Mestre@123"
    session_hours: int = 12
    seed: bool = True


def load_config(**overrides: object) -> Config:
    _load_dotenv()
    values: dict[str, object] = {
        "host": os.getenv("HOST", "127.0.0.1"),
        "port": int(os.getenv("PORT", "3000")),
        "database_path": os.getenv("DATABASE_PATH", "./data/rpg.sqlite"),
        "master_name": os.getenv("MESTRE_NAME", "Mestre do Jogo"),
        "master_email": os.getenv("MESTRE_EMAIL", "mestre@rpg.local").lower(),
        "master_password": os.getenv("MESTRE_PASSWORD", "Mestre@123"),
        "session_hours": int(os.getenv("SESSION_HOURS", "12")),
        "seed": True,
    }
    values.update({key: value for key, value in overrides.items() if value is not None})
    return Config(**values)
