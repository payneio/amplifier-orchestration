"""Shared test fixtures and utilities."""

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def foreman_config() -> dict:
    """Create test foreman configuration.

    Returns:
        Foreman mount plan configuration dictionary
    """
    return {
        "behaviors": {"context": {"provider": "context-anthropic"}},
        "tools": {"issue_manager": {"provider": "tool-issue"}},
    }


@pytest.fixture
def coding_worker_config() -> dict:
    """Create test coding worker configuration.

    Returns:
        Coding worker mount plan configuration dictionary
    """
    return {
        "behaviors": {"context": {"provider": "context-anthropic"}},
        "tools": {
            "issue_manager": {"provider": "tool-issue"},
            "read_file": {"provider": "tool-filesystem"},
        },
    }


@pytest.fixture
def research_worker_config() -> dict:
    """Create test research worker configuration.

    Returns:
        Research worker mount plan configuration dictionary
    """
    return {
        "behaviors": {"context": {"provider": "context-anthropic"}},
        "tools": {"issue_manager": {"provider": "tool-issue"}},
    }


@pytest.fixture
def temp_mount_plans_dir(tmp_path: Path) -> Path:
    """Create temporary directory with test mount plans.

    Args:
        tmp_path: pytest temporary directory fixture

    Returns:
        Path to temporary mount plans directory
    """
    mount_plans_dir = tmp_path / "mount_plans"
    mount_plans_dir.mkdir()

    # Create valid foreman mount plan
    foreman_plan = {
        "behaviors": {"context": {"provider": "context-anthropic"}},
        "tools": {"issue_manager": {"provider": "tool-issue"}},
    }
    (mount_plans_dir / "foreman.json").write_text(json.dumps(foreman_plan))

    # Create valid worker mount plans
    coding_plan = {
        "behaviors": {"context": {"provider": "context-anthropic"}},
        "tools": {
            "issue_manager": {"provider": "tool-issue"},
            "read_file": {"provider": "tool-filesystem"},
        },
    }
    (mount_plans_dir / "coding-worker.json").write_text(json.dumps(coding_plan))

    research_plan = {
        "behaviors": {"context": {"provider": "context-anthropic"}},
        "tools": {"issue_manager": {"provider": "tool-issue"}},
    }
    (mount_plans_dir / "research-worker.json").write_text(json.dumps(research_plan))

    return mount_plans_dir


@pytest.fixture
def mock_loader() -> MagicMock:
    """Create mock ModuleLoader.

    Returns:
        Mocked ModuleLoader instance
    """
    return MagicMock()


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock AmplifierSession.

    Returns:
        Mocked AmplifierSession with async context manager support
    """
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    # Mock coordinator with context manager
    mock_context = AsyncMock()
    mock_context.add_message = AsyncMock()
    session.coordinator = MagicMock()
    session.coordinator.get = MagicMock(return_value=mock_context)

    # Mock execute method
    session.execute = AsyncMock(return_value="Foreman response")

    return session


@pytest.fixture
def mock_session_factory(mock_session: AsyncMock) -> MagicMock:
    """Create factory that returns mock sessions.

    Args:
        mock_session: Base mock session to return

    Returns:
        Factory function that creates mock sessions
    """
    def factory(*args: Any, **kwargs: Any) -> AsyncMock:
        # Create new session for each call to avoid state sharing
        new_session = AsyncMock()
        new_session.__aenter__ = AsyncMock(return_value=new_session)
        new_session.__aexit__ = AsyncMock(return_value=None)

        mock_context = AsyncMock()
        mock_context.add_message = AsyncMock()
        new_session.coordinator = MagicMock()
        new_session.coordinator.get = MagicMock(return_value=mock_context)
        new_session.execute = AsyncMock(return_value="Worker response: no work")

        return new_session

    return MagicMock(side_effect=factory)


@pytest.fixture
def workspace_dir(tmp_path: Path) -> Path:
    """Create temporary workspace directory.

    Args:
        tmp_path: pytest temporary directory fixture

    Returns:
        Path to temporary workspace directory
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
async def event_loop_yield() -> None:
    """Yield control to event loop to allow other tasks to run.

    Useful for testing that background tasks get scheduled.
    """
    await asyncio.sleep(0.01)
