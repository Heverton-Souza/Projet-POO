from collections import defaultdict
from collections.abc import Callable

from app.application.ports import EventPublisher
from app.domain.events import DomainEvent


class InMemoryEventPublisher(EventPublisher):
    """Observer síncrono e simples, adequado ao escopo do projeto."""

    def __init__(self) -> None:
        self.handlers: dict[str, list[Callable[[DomainEvent], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None:
        self.handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in [*self.handlers[event.type], *self.handlers["*"]]:
            handler(event)

