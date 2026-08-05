"""Auditable scientific tool boundary."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from ..contracts import (
    CoverageStatus, EvidenceItem, TaskSpec, ToolCapability, ToolDescriptor,
    ToolResult, ToolStatus,
)
from ..settings import Settings, load_settings


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
    prior_results: list[ToolResult] = field(default_factory=list)
    settings: Settings = field(default_factory=load_settings)
    attempt: int = 0


class ScientificTool(ABC):
    name: str
    version: str
    descriptor: ToolDescriptor

    @abstractmethod
    def run(self, context: ToolContext) -> ToolExecution:
        raise NotImplementedError


def execute_tool_safely(tool: ScientificTool, context: ToolContext) -> ToolExecution:
    """Convert unexpected tool exceptions into a traceable failed ToolResult."""
    try:
        return tool.run(context)
    except Exception as exc:  # scientific workflow must retain a structured terminal path
        message = str(exc)
        for path in (context.run_dir, context.cache_dir, context.settings.input_root):
            message = message.replace(str(path), "[configured-path]")
        for secret_name in ("step_api_key", "ncbi_api_key"):
            secret = getattr(context.settings, secret_name, None)
            if secret:
                value = secret.get_secret_value()
                if value:
                    message = message.replace(value, "[redacted]")
        return ToolExecution(result=ToolResult(
            tool_name=tool.name, tool_version=tool.version,
            status=ToolStatus.FAILED, coverage_status=CoverageStatus.UNKNOWN,
            context_match_score=0.0, inputs={}, outputs={},
            capability=ToolCapability(validation_scope="unexpected tool exception"),
            error=f"{exc.__class__.__name__}: {message[:500]}",
            limitations=["The tool raised an unexpected exception; no scientific output was accepted."],
        ), evidence=[])


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

    @property
    def descriptors(self) -> list[ToolDescriptor]:
        return [
            getattr(
                self._tools[name],
                "descriptor",
                ToolDescriptor(
                    tool_id=name,
                    evidence_dimension="causal_gold" if name == "mch_causal_gold" else "perturbation",
                    description=f"Scoped legacy plugin: {name}",
                    enabled=True,
                ),
            )
            for name in self.names
        ]

    def public_capabilities(self) -> list[dict]:
        return [descriptor.model_dump(mode="json") for descriptor in self.descriptors]
