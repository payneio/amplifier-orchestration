"""Integration tests for ForemanWorkerOrchestrator."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplifier_orchestrator_foreman_worker import ForemanWorkerOrchestrator, WorkerConfig


class TestForemanInitialization:
    """Test foreman initialization and message handling."""

    @pytest.mark.asyncio
    async def test_foreman_initializes_on_first_message(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test foreman initializes lazily on first message."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.execute = AsyncMock(return_value="Response")

            mock_context = AsyncMock()
            mock_session.coordinator = MagicMock()
            mock_session.coordinator.get = MagicMock(return_value=mock_context)

            mock_session_class.return_value = mock_session

            assert not orchestrator._initialized

            response = await orchestrator.execute_user_message("Test message")

            assert orchestrator._initialized
            assert orchestrator.foreman_session is not None
            assert response == "Response"

    @pytest.mark.asyncio
    async def test_foreman_only_initializes_once(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test foreman initializes only on first message."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.execute = AsyncMock(return_value="Response")

            mock_context = AsyncMock()
            mock_session.coordinator = MagicMock()
            mock_session.coordinator.get = MagicMock(return_value=mock_context)

            mock_session_class.return_value = mock_session

            # First message
            await orchestrator.execute_user_message("Message 1")
            first_session = orchestrator.foreman_session

            # Second message
            await orchestrator.execute_user_message("Message 2")
            second_session = orchestrator.foreman_session

            # Should be the same session
            assert first_session is second_session

            # Session should only be created once
            assert mock_session_class.call_count == 1

    @pytest.mark.asyncio
    async def test_foreman_receives_system_instructions(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test foreman receives correct system instructions."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.execute = AsyncMock(return_value="Response")

            mock_context = AsyncMock()
            mock_context.add_message = AsyncMock()
            mock_session.coordinator = MagicMock()
            mock_session.coordinator.get = MagicMock(return_value=mock_context)

            mock_session_class.return_value = mock_session

            await orchestrator.execute_user_message("Test")

            # Verify system instructions were added
            mock_context.add_message.assert_called_once()
            call_args = mock_context.add_message.call_args[0][0]

            assert call_args["role"] == "system"
            assert "Foreman" in call_args["content"]
            assert "issue_manager" in call_args["content"]

    @pytest.mark.asyncio
    async def test_foreman_execution_error_handling(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test foreman execution handles errors properly."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.execute = AsyncMock(side_effect=RuntimeError("Execution failed"))

            mock_context = AsyncMock()
            mock_session.coordinator = MagicMock()
            mock_session.coordinator.get = MagicMock(return_value=mock_context)

            mock_session_class.return_value = mock_session

            with pytest.raises(RuntimeError, match="Foreman execution failed"):
                await orchestrator.execute_user_message("Test")


class TestEventLoopFairness:
    """Test that workers get CPU time during foreman execution."""

    @pytest.mark.asyncio
    async def test_workers_get_scheduled_during_foreman_execution(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test workers can run while foreman is executing.

        This tests the hybrid async approach where foreman execution
        yields control periodically to allow worker tasks to run.
        """
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=[WorkerConfig(profile="coding-worker", count=1)],
            workspace_root=workspace_dir,
        )

        worker_executed = asyncio.Event()

        # Track if worker task actually runs
        async def mock_worker_that_sets_flag(*args, **kwargs):
            worker_executed.set()
            # Simulate quick worker execution
            await asyncio.sleep(0.01)
            return "Worker done"

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            mock_context = AsyncMock()

            def create_foreman_session(config, **kwargs):
                session = AsyncMock()
                session.__aenter__ = AsyncMock(return_value=session)
                session.__aexit__ = AsyncMock()

                async def slow_foreman_execute(message):
                    # Simulate LLM call taking time
                    await asyncio.sleep(0.3)
                    return "Foreman response"

                session.execute = AsyncMock(side_effect=slow_foreman_execute)
                session.coordinator = MagicMock()
                session.coordinator.get = MagicMock(return_value=mock_context)
                return session

            def create_worker_session(config, **kwargs):
                session = AsyncMock()
                session.__aenter__ = AsyncMock(return_value=session)
                session.__aexit__ = AsyncMock()
                session.execute = AsyncMock(side_effect=mock_worker_that_sets_flag)
                session.coordinator = MagicMock()
                session.coordinator.get = MagicMock(return_value=mock_context)
                return session

            # Return different sessions based on creation order
            # First call is foreman, subsequent are workers
            session_count = {"count": 0}

            def session_factory(config, **kwargs):
                session_count["count"] += 1
                if session_count["count"] == 1:
                    # First session is foreman
                    return create_foreman_session(config, **kwargs)
                # Subsequent sessions are workers
                return create_worker_session(config, **kwargs)

            mock_session_class.side_effect = session_factory

            # Execute foreman message (which should also allow workers to run)
            async with orchestrator:
                response = await orchestrator.execute_user_message("Create a task")

                # Give workers a moment to execute
                await asyncio.sleep(0.1)

            # Verify worker got to execute
            assert worker_executed.is_set(), "Worker task should have been scheduled and executed"
            assert response == "Foreman response"


class TestWorkerTaskProcessing:
    """Test worker task claiming and processing."""

    @pytest.mark.asyncio
    async def test_worker_receives_system_instructions(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test worker receives correct system instructions."""
        worker_configs = [WorkerConfig(profile="coding-worker", count=1)]

        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            mount_plans_dir=temp_mount_plans_dir,
            foreman_profile="foreman",
            worker_configs=worker_configs,
            workspace_root=workspace_dir,
        )

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            sessions_created = []

            def track_sessions(config, **kwargs):
                session = AsyncMock()
                session.__aenter__ = AsyncMock(return_value=session)
                session.__aexit__ = AsyncMock()
                session.execute = AsyncMock(return_value="no work")

                mock_context = AsyncMock()
                session.coordinator = MagicMock()
                session.coordinator.get = MagicMock(return_value=mock_context)

                sessions_created.append(session)
                return session

            mock_session_class.side_effect = track_sessions

            async with orchestrator:
                await orchestrator.execute_user_message("Test")

                # Give worker time to start
                await asyncio.sleep(0.1)

            # Should have created foreman + 1 worker session
            assert len(sessions_created) >= 2

            # Find worker session (not the foreman)
            worker_session = None
            for session in sessions_created[1:]:  # Skip foreman
                if session.coordinator.get.called:
                    worker_session = session
                    break

            assert worker_session is not None

            # Check worker received system instructions
            worker_context = worker_session.coordinator.get.return_value
            assert worker_context.add_message.called

            call_args = worker_context.add_message.call_args[0][0]
            assert call_args["role"] == "system"
            assert "worker" in call_args["content"].lower()

    @pytest.mark.asyncio
    async def test_multiple_workers_coexist(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test multiple workers can coexist and run independently."""
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
            session_count = {"count": 0}

            def create_session(config, **kwargs):
                session = AsyncMock()
                session.__aenter__ = AsyncMock(return_value=session)
                session.__aexit__ = AsyncMock()
                session.execute = AsyncMock(return_value="no work")

                mock_context = AsyncMock()
                session.coordinator = MagicMock()
                session.coordinator.get = MagicMock(return_value=mock_context)

                session_count["count"] += 1
                return session

            mock_session_class.side_effect = create_session

            async with orchestrator:
                await orchestrator.execute_user_message("Test")

                # Give workers time to start
                await asyncio.sleep(0.1)

                # Verify all workers are running
                assert len(orchestrator.worker_tasks) == 3

                # All tasks should be alive
                for task in orchestrator.worker_tasks:
                    assert not task.done()


class TestFullWorkflow:
    """Test complete foreman-worker workflow."""

    @pytest.mark.asyncio
    async def test_orchestrator_lifecycle(
        self, mock_loader: MagicMock, temp_mount_plans_dir: Path, workspace_dir: Path
    ):
        """Test complete lifecycle: start, process messages, shutdown."""
        worker_configs = [WorkerConfig(profile="coding-worker", count=1)]

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
            mock_session.execute = AsyncMock(return_value="Response")

            mock_context = AsyncMock()
            mock_session.coordinator = MagicMock()
            mock_session.coordinator.get = MagicMock(return_value=mock_context)

            mock_session_class.return_value = mock_session

            # Start
            async with orchestrator:
                # Not initialized yet
                assert not orchestrator._initialized

                # Process first message - triggers initialization
                response1 = await orchestrator.execute_user_message("Message 1")
                assert orchestrator._initialized
                assert response1 == "Response"

                # Process second message
                response2 = await orchestrator.execute_user_message("Message 2")
                assert response2 == "Response"

                # Workers should be running
                assert len(orchestrator.worker_tasks) == 1

            # After context exit, should be shut down
            assert orchestrator._shutdown_event.is_set()
