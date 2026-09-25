from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class TaskBaseline:
    day: date
    client: str
    due_today_ids: frozenset[str]
    overdue_ids: frozenset[str]
    task_types: dict[str, str]

    @property
    def total(self) -> int:
        return len(self.due_today_ids | self.overdue_ids)


@dataclass(frozen=True)
class TaskProgress:
    completed: int
    total: int
    pending_today: int
    pending_overdue: int

    @property
    def percent(self) -> int:
        return round(100 * self.completed / self.total) if self.total else 0


@dataclass(frozen=True)
class CallMetrics:
    calls: int
    unique_contacts: int
    repeated_contacts: int
    answered: int
    unanswered: int
    relevant_conversations: int
    conversation_seconds: int
    phone_seconds: int


@dataclass(frozen=True)
class OperationalGap:
    start: datetime
    end: datetime

    @property
    def seconds(self) -> int:
        return max(0, int((self.end - self.start).total_seconds()))
