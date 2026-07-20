"""BaseAgent: the perceive -> reason -> act loop every agent shares."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from .llm import LLMBackend
from .message import Message, Role
from .tools import ToolRegistry

log = logging.getLogger("agentflow")


class BaseAgent(ABC):
    role: Role

    def __init__(self, llm: LLMBackend, tools: ToolRegistry) -> None:
        self.llm = llm
        self.tools = tools
        self.memory: list[Message] = []   # per-agent episodic memory

    def receive(self, msg: Message) -> Message:
        """Standard entry point: log, remember, delegate to handle()."""
        log.info("%s received %r", self.role.value, msg)
        self.memory.append(msg)
        reply = self.handle(msg)
        self.memory.append(reply)
        log.info("%s replying %r", self.role.value, reply)
        return reply

    @abstractmethod
    def handle(self, msg: Message) -> Message:
        """Role-specific behaviour, implemented by each agent."""
