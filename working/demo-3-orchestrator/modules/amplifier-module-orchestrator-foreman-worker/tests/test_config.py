"""Unit tests for configuration module."""

import pytest

from amplifier_orchestrator_foreman_worker.config import WorkerConfig


class TestWorkerConfig:
    """Test WorkerConfig dataclass."""

    def test_create_worker_config(self):
        """Test creating WorkerConfig with valid values."""
        worker_config = WorkerConfig(name="coding-worker", config={"key": "value"}, count=2)

        assert worker_config.name == "coding-worker"
        assert worker_config.config == {"key": "value"}
        assert worker_config.count == 2

    def test_worker_config_fields(self):
        """Test WorkerConfig has expected fields."""
        worker_config = WorkerConfig(name="test", config={}, count=1)

        assert hasattr(worker_config, "name")
        assert hasattr(worker_config, "config")
        assert hasattr(worker_config, "count")

    def test_worker_config_equality(self):
        """Test WorkerConfig equality comparison."""
        config1 = WorkerConfig(name="coding-worker", config={"key": "val"}, count=2)
        config2 = WorkerConfig(name="coding-worker", config={"key": "val"}, count=2)
        config3 = WorkerConfig(name="research-worker", config={}, count=1)

        assert config1 == config2
        assert config1 != config3
