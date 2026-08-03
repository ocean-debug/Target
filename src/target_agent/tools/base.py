"""Auditable scientific tool boundary."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ..contracts import EvidenceItem, TaskSpec, ToolResult


@dataclass
class ToolExecution:
    result: ToolResult
    evidence: list[EvidenceItem]


@dataclass
class ToolContext:
    task: TaskSpec
    run_dir: Path
    cache_dir: Path
    candidate_genes: list[str]


class ScientificTool(ABC):
    name: str
    version: str

    @abstractmethod
    def run(self, context: ToolContext) -> ToolExecution:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self, tools: list[ScientificTool]):
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: str) -> ScientificTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ValueError(f"tool is not whitelisted: {name}") from exc

    @property
    def names(self) -> list[str]:
        return sorted(self._tools)

