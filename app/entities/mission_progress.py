from dataclasses import dataclass
from typing import Any

from app.domain.enums import MissionStatus
from app.domain.errors import ConflictError


@dataclass
class MissionProgress:
    id: str
    character_id: str
    mission_id: str
    target: int
    status: MissionStatus = MissionStatus.ACCEPTED
    progress: int = 0
    accepted_at: str | None = None
    completed_at: str | None = None
    title: str = ""
    objective: str = ""

    def __post_init__(self) -> None:
        self.status = MissionStatus(self.status)

    def update(self, amount: int) -> None:
        if self.status not in {MissionStatus.ACCEPTED, MissionStatus.IN_PROGRESS}:
            raise ConflictError("Esta missão não permite atualização de progresso.")
        self.status = MissionStatus.IN_PROGRESS
        self.progress = min(self.target, self.progress + max(0, amount))

    def complete(self) -> None:
        if self.progress < self.target:
            raise ConflictError("Todos os objetivos devem ser cumpridos antes de concluir a missão.")
        self.status = MissionStatus.COMPLETED

    def cancel(self) -> None:
        if self.status in {MissionStatus.COMPLETED, MissionStatus.CANCELLED}:
            raise ConflictError("Esta missão já foi finalizada.")
        self.status = MissionStatus.CANCELLED

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "characterId": self.character_id,
            "missionId": self.mission_id,
            "status": self.status.value,
            "progress": self.progress,
            "target": self.target,
            "acceptedAt": self.accepted_at,
            "completedAt": self.completed_at,
            "title": self.title,
            "objective": self.objective,
        }
