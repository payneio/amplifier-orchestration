"""Configuration types for foreman-worker orchestrator."""

from dataclasses import dataclass


@dataclass
class WorkerConfig:
    """Configuration for a worker type.

    Args:
        name: Worker type name (e.g., "coding-worker")
        config: Mount plan configuration dictionary
        count: Number of worker instances to spawn
    """

    name: str
    config: dict
    count: int
