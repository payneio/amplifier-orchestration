"""Observer orchestrator module for Amplifier.

Implements the observer pattern for bottom-up feedback loops where:
- A main session does actual work (research, coding, writing)
- Observer sessions watch output and create feedback issues
- The main session addresses feedback in iterative rounds
- Process converges when observers have no more feedback

This is the inverse of the foreman-worker pattern:
- Foreman-Worker: Top-down delegation
- Observer: Bottom-up feedback

Exports:
    ObserverOrchestrator - Main orchestrator class
    ObserverConfig - Observer configuration dataclass
"""

# Amplifier module metadata
__amplifier_module_type__ = "orchestrator"

from .config import ObserverConfig
from .orchestrator import ObserverOrchestrator

__all__ = ["ObserverOrchestrator", "ObserverConfig"]
