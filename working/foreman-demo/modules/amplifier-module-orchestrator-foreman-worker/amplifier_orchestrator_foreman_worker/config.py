"""Configuration types for foreman-worker orchestrator."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Configuration for a worker type.

    Args:
        profile: Mount plan name (e.g., "coding-worker")
        count: Number of worker instances to spawn
    """

    profile: str
    count: int


def load_mount_plan(mount_plans_dir: Path, profile: str) -> dict:
    """Load mount plan from JSON file.

    Args:
        mount_plans_dir: Directory containing mount plan JSON files
        profile: Name of the profile (filename without .json)

    Returns:
        Mount plan configuration dictionary

    Raises:
        FileNotFoundError: If mount plan file doesn't exist
        ValueError: If JSON is invalid
    """
    mount_plan_path = mount_plans_dir / f"{profile}.json"

    if not mount_plan_path.exists():
        raise FileNotFoundError(f"Mount plan not found: {mount_plan_path}")

    try:
        with open(mount_plan_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {mount_plan_path}: {e}")
