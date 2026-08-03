"""Default scientific tool registry."""
from .base import ToolRegistry
from .literature import EuropePMCRAGTool
from .mch import MCHCausalGoldTool
from .opentargets import OpenTargetsTool
from .uc import DeltaFactorTool, ObservedTCellPerturbationTool, UCOmicsSnapshotTool


def default_registry() -> ToolRegistry:
    return ToolRegistry([
        UCOmicsSnapshotTool(),
        OpenTargetsTool(),
        EuropePMCRAGTool(),
        ObservedTCellPerturbationTool(),
        DeltaFactorTool(),
        MCHCausalGoldTool(),
    ])


__all__ = ["default_registry", "ToolRegistry"]

