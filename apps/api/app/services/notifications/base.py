from dataclasses import dataclass
from typing import Protocol


@dataclass
class SendResult:
    ok: bool
    status: str
    error: str | None = None
    duration_ms: int = 0


class Notifier(Protocol):
    channel: str

    def send(self, destination: dict, subject: str, body: str) -> SendResult: ...