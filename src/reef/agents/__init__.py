"""
Reef agent infrastructure - localized agents with orchestration.

Agents:
- orchestrator: Coordinates reef agent operations
- strategist: Strategic task decomposition
- validator: Karen-style validation
- researcher: Web/code research
- worker: External model dispatch
"""

from .orchestrator import ReefOrchestrator
from .strategist import ReefStrategist
from .validator import ReefValidator

__all__ = ['ReefOrchestrator', 'ReefStrategist', 'ReefValidator']
