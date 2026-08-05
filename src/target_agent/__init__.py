"""TargetDiscovery Agent package.

Modules are intentionally empty at project initialization. Implementations must
follow the versioned contracts under schemas/ and the ownership rules under docs/.
"""

__all__: list[str] = []
"""TargetDiscovery Agent public package."""

from .contracts import CONTRACT_VERSION, TaskSpec
from .research_contracts import RESEARCH_CONTRACT_VERSION, ResearchProjectSpec
from .research_runtime import ResearchProjectRuntime
from .runtime import TargetDiscoveryRuntime

__all__ = [
    "CONTRACT_VERSION", "RESEARCH_CONTRACT_VERSION", "ResearchProjectRuntime",
    "ResearchProjectSpec", "TaskSpec", "TargetDiscoveryRuntime",
]
__version__ = "0.4.0"
