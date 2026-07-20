"""Message protocol shared by all agents.

Every inter-agent communication is a typed Message. Keeping the protocol
explicit (instead of passing raw strings) makes the system observable,
testable, and easy to extend with new agent roles.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Role(str, Enum):
    ORCHESTRATOR = "orchestrator"
    PLANNER = "planner"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    REPORTER = "reporter"


class MessageType(str, Enum):
    TASK = "task"            # a unit of work assigned to an agent
    RESULT = "result"        # output of a completed task
    REVIEW = "review"        # reviewer verdict on a result
    ERROR = "error"          # failure report


@dataclass
class Message:
    sender: Role
    recipient: Role
    type: MessageType
    content: dict[str, Any]
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    ts: float = field(default_factory=time.time)

    def __repr__(self) -> str:  # compact trace-friendly repr
        return f"<{self.sender.value} -> {self.recipient.value} [{self.type.value}] {self.id}>"


@dataclass
class PlanStep:
    """One step of an execution plan produced by the Planner."""
    step_id: int
    tool: str
    args: dict[str, Any]
    rationale: str
    status: str = "pending"          # pending | done | failed
    result: Any = None
