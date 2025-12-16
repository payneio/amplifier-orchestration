"""Unit tests for configuration module."""

import json
from pathlib import Path

import pytest

from amplifier_orchestrator_foreman_worker.config import WorkerConfig, load_mount_plan


class TestWorkerConfig:
    """Test WorkerConfig dataclass."""

    def test_create_worker_config(self):
        """Test creating WorkerConfig with valid values."""
        config = WorkerConfig(profile="coding-worker", count=2)

        assert config.profile == "coding-worker"
        assert config.count == 2

    def test_worker_config_fields(self):
        """Test WorkerConfig has expected fields."""
        config = WorkerConfig(profile="test", count=1)

        assert hasattr(config, "profile")
        assert hasattr(config, "count")

    def test_worker_config_equality(self):
        """Test WorkerConfig equality comparison."""
        config1 = WorkerConfig(profile="coding-worker", count=2)
        config2 = WorkerConfig(profile="coding-worker", count=2)
        config3 = WorkerConfig(profile="research-worker", count=1)

        assert config1 == config2
        assert config1 != config3


class TestLoadMountPlan:
    """Test load_mount_plan function."""

    def test_load_valid_mount_plan(self, temp_mount_plans_dir: Path):
        """Test loading a valid mount plan."""
        config = load_mount_plan(temp_mount_plans_dir, "foreman")

        assert isinstance(config, dict)
        assert "behaviors" in config
        assert "tools" in config

    def test_load_nonexistent_mount_plan(self, temp_mount_plans_dir: Path):
        """Test loading nonexistent mount plan raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Mount plan not found"):
            load_mount_plan(temp_mount_plans_dir, "nonexistent")

    def test_load_invalid_json(self, tmp_path: Path):
        """Test loading invalid JSON raises ValueError."""
        mount_plans_dir = tmp_path / "invalid_plans"
        mount_plans_dir.mkdir()

        # Create file with invalid JSON
        invalid_file = mount_plans_dir / "invalid.json"
        invalid_file.write_text("{ invalid json }")

        with pytest.raises(ValueError, match="Invalid JSON"):
            load_mount_plan(mount_plans_dir, "invalid")

    def test_load_empty_json(self, tmp_path: Path):
        """Test loading empty JSON file."""
        mount_plans_dir = tmp_path / "empty_plans"
        mount_plans_dir.mkdir()

        # Create file with empty JSON object
        empty_file = mount_plans_dir / "empty.json"
        empty_file.write_text("{}")

        config = load_mount_plan(mount_plans_dir, "empty")
        assert config == {}

    def test_load_complex_mount_plan(self, tmp_path: Path):
        """Test loading mount plan with complex structure."""
        mount_plans_dir = tmp_path / "complex_plans"
        mount_plans_dir.mkdir()

        complex_plan = {
            "behaviors": {
                "context": {"provider": "context-anthropic", "config": {"model": "claude-3"}},
                "memory": {"provider": "memory-simple"},
            },
            "tools": {
                "issue_manager": {"provider": "tool-issue"},
                "filesystem": {"provider": "tool-filesystem", "config": {"root": "/tmp"}},
            },
        }

        plan_file = mount_plans_dir / "complex.json"
        plan_file.write_text(json.dumps(complex_plan))

        config = load_mount_plan(mount_plans_dir, "complex")

        assert config == complex_plan
        assert config["behaviors"]["context"]["config"]["model"] == "claude-3"
        assert config["tools"]["filesystem"]["config"]["root"] == "/tmp"
