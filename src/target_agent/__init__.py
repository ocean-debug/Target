"""TargetDiscovery Agent package.

Modules are intentionally empty at project initialization. Implementations must
follow the versioned contracts under schemas/ and the ownership rules under docs/.
"""

__all__: list[str] = []
"""TargetDiscovery Agent public package."""

from .contracts import CONTRACT_VERSION, TaskSpec
from .runtime import TargetDiscoveryRuntime

__all__ = ["CONTRACT_VERSION", "TaskSpec", "TargetDiscoveryRuntime"]
__version__ = "0.3.0"
