"""Unit tests for ForemanWorkerOrchestrator class."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplifier_orchestrator_foreman_worker import ForemanWorkerOrchestrator, WorkerConfig


class TestOrchestratorInitialization:
    """Test orchestrator initialization."""

    def test_create_orchestrator(self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path):
        """Test creating orchestrator with valid configuration."""
        worker_configs = [
            WorkerConfig(profile="coding-worker", count=2),
            WorkerConfig(profile="research-worker", count=1),
        ]

        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=worker_configs,
            workspace_root=workspace_dir,
        )

        assert orchestrator.loader == mock_loader
        assert orchestrator.mount_plans_dir == temp_mount_plans_dir
        assert orchestrator.foreman_profile == "foreman"
        assert orchestrator.worker_configs == worker_configs
        assert orchestrator.workspace_root == workspace_dir
        assert orchestrator.foreman_session is None
        assert orchestrator.worker_tasks == []
        assert orchestrator._initialized is False

    def test_create_orchestrator_with_systems(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test creating orchestrator with approval and display systems."""
        approval_system = MagicMock()
        display_system = MagicMock()

        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
            approval_system=approval_system,
            display_system=display_system,
        )

        assert orchestrator.approval_system == approval_system
        assert orchestrator.display_system == display_system

    def test_orchestrator_initial_state(self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path):
        """Test orchestrator starts with correct initial state."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        assert not orchestrator._initialized
        assert orchestrator.foreman_session is None
        assert len(orchestrator.worker_tasks) == 0
        assert not orchestrator._shutdown_event.is_set()


class TestOrchestratorContextManager:
    """Test orchestrator context manager protocol."""

    @pytest.mark.asyncio
    async def test_context_manager_entry(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test entering orchestrator context manager."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        async with orchestrator as orch:
            assert orch is orchestrator

    @pytest.mark.asyncio
    async def test_context_manager_exit_calls_shutdown(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test exiting context manager calls shutdown."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        with patch.object(orchestrator, "shutdown", new_callable=AsyncMock) as mock_shutdown:
            async with orchestrator:
                pass

            mock_shutdown.assert_called_once()


class TestOrchestratorShutdown:
    """Test orchestrator shutdown behavior."""

    @pytest.mark.asyncio
    async def test_shutdown_before_initialization(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test shutdown before initialization does nothing."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        # Should not raise
        await orchestrator.shutdown()

        assert not orchestrator._initialized

    @pytest.mark.asyncio
    async def test_shutdown_sets_event(self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path):
        """Test shutdown sets shutdown event."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        # Simulate initialization
        orchestrator._initialized = True

        await orchestrator.shutdown()

        assert orchestrator._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_shutdown_waits_for_workers(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test shutdown waits for all worker tasks."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        # Simulate initialization with worker tasks
        orchestrator._initialized = True

        # Create mock worker tasks that complete immediately
        async def mock_worker():
            await asyncio.sleep(0.01)

        task1 = asyncio.create_task(mock_worker())
        task2 = asyncio.create_task(mock_worker())
        orchestrator.worker_tasks = [task1, task2]

        await orchestrator.shutdown()

        # Verify tasks completed
        assert task1.done()
        assert task2.done()

    @pytest.mark.asyncio
    async def test_shutdown_closes_foreman_session(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test shutdown closes foreman session."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        # Simulate initialization with mock foreman session
        orchestrator._initialized = True
        mock_session = AsyncMock()
        mock_session.__aexit__ = AsyncMock()
        orchestrator.foreman_session = mock_session

        await orchestrator.shutdown()

        mock_session.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_handles_worker_exceptions(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test shutdown handles worker task exceptions gracefully."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        # Simulate initialization
        orchestrator._initialized = True

        # Create worker task that raises exception
        async def failing_worker():
            raise RuntimeError("Worker error")

        task = asyncio.create_task(failing_worker())
        orchestrator.worker_tasks = [task]

        # Should not raise - exceptions are suppressed by return_exceptions=True
        await orchestrator.shutdown()

        assert task.done()


class TestOrchestratorWorkerManagement:
    """Test worker lifecycle management."""

    @pytest.mark.asyncio
    async def test_worker_count_matches_config(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test correct number of workers are created."""
        worker_configs = [
            WorkerConfig(profile="coding-worker", count=2),
            WorkerConfig(profile="research-worker", count=1),
        ]

        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=worker_configs,
            workspace_root=workspace_dir,
        )

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_context = AsyncMock()
            mock_session.coordinator = MagicMock()
            mock_session.coordinator.get = MagicMock(return_value=mock_context)
            mock_session_class.return_value = mock_session

            # Start workers
            await orchestrator._start_workers()

            # Should have 3 worker tasks (2 + 1)
            assert len(orchestrator.worker_tasks) == 3

    @pytest.mark.asyncio
    async def test_worker_ids_are_unique(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test each worker gets a unique ID."""
        worker_configs = [
            WorkerConfig(profile="coding-worker", count=3),
        ]

        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=worker_configs,
            workspace_root=workspace_dir,
        )

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession"):
            await orchestrator._start_workers()

            # Get task names (which should be worker IDs)
            task_names = [task.get_name() for task in orchestrator.worker_tasks]

            # All names should be unique
            assert len(task_names) == len(set(task_names))

            # Names should follow pattern
            assert "coding-worker-0" in task_names
            assert "coding-worker-1" in task_names
            assert "coding-worker-2" in task_names

    @pytest.mark.asyncio
    async def test_empty_worker_config(self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path):
        """Test orchestrator with no workers configured."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        await orchestrator._start_workers()

        assert len(orchestrator.worker_tasks) == 0
