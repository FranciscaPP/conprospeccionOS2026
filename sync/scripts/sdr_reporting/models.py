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
    today_done: int
    today_total: int
    pending_today: int
    pending_overdue: int

    @property
    def percent(self) -> int:
        return round(100 * self.today_done / self.today_total) if self.today_total else 0

    @property
    def completed(self) -> int:
        return self.today_done

    @property
    def total(self) -> int:
        return self.today_total


@dataclass(frozen=True)
class CallMetrics:
    calls: int
    unique_contacts: int
    answered: int
    unanswered: int
    retry_calls: int
    answered_seconds: int
    unanswered_phone_seconds: int
    retry_phone_seconds: int
    phone_seconds: int

    @property
    def repeated_contacts(self) -> int:
        return self.retry_calls

    @property
    def conversation_seconds(self) -> int:
        return self.answered_seconds

    @property
    def relevant_conversations(self) -> int:
        return self.answered


@dataclass(frozen=True)
class OperationalGap:
    start: datetime
    end: datetime

    @property
    def seconds(self) -> int:
        return max(0, int((self.end - self.start).total_seconds()))
