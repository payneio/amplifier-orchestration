"""Edge case and error handling tests."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplifier_orchestrator_foreman_worker import ForemanWorkerOrchestrator, WorkerConfig


class TestInvalidConfiguration:
    """Test handling of invalid configurations."""

    @pytest.mark.asyncio
    async def test_invalid_foreman_mount_plan(
        self, mock_loader: MagicMock, workspace_dir: Path
    ):
        """Test error when foreman config causes AmplifierSession to fail."""
        # With the new design, config is passed directly, so invalid config
        # manifests as AmplifierSession initialization failure
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            foreman_config={"invalid": "config"},
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            mock_session_class.side_effect = ValueError("Invalid configuration")

            with pytest.raises(ValueError, match="Invalid configuration"):
                await orchestrator.execute_user_message("Test")

    @pytest.mark.asyncio
    async def test_invalid_worker_mount_plan(
        self, mock_loader: MagicMock, foreman_config: dict, workspace_dir: Path
    ):
        """Test error when worker config causes session to fail."""
        worker_configs = [WorkerConfig(name="bad-worker", config={"invalid": "config"}, count=1)]

        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            foreman_config=foreman_config,
            worker_configs=worker_configs,
            workspace_root=workspace_dir,
        )

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            # Foreman session succeeds
            foreman_session = AsyncMock()
            foreman_session.__aenter__ = AsyncMock(return_value=foreman_session)
            foreman_session.__aexit__ = AsyncMock()
            foreman_session.execute = AsyncMock(return_value="Response")

            mock_context = AsyncMock()
            foreman_session.coordinator = MagicMock()
            foreman_session.coordinator.get = MagicMock(return_value=mock_context)

            mock_session_class.return_value = foreman_session

            async with orchestrator:
                # Should initialize without error
                await orchestrator.execute_user_message("Test")

                # Give workers time to fail
                await asyncio.sleep(0.1)

                # Worker tasks should exist but may have failed
                assert len(orchestrator.worker_tasks) == 1

    @pytest.mark.asyncio
    async def test_missing_context_manager_in_foreman(
        self, mock_loader: MagicMock, foreman_config: dict, workspace_dir: Path
    ):
        """Test error when foreman session has no context manager."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            foreman_config=foreman_config,
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)

            # Context manager returns None
            mock_session.coordinator = MagicMock()
            mock_session.coordinator.get = MagicMock(return_value=None)

            mock_session_class.return_value = mock_session

            with pytest.raises(RuntimeError, match="No context manager mounted"):
                await orchestrator.execute_user_message("Test")


class TestConcurrentOperations:
    """Test concurrent foreman messages and worker operations."""

    @pytest.mark.asyncio
    async def test_concurrent_foreman_messages(
        self, mock_loader: MagicMock, foreman_config: dict, workspace_dir: Path
    ):
        """Test handling multiple concurrent foreman messages."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            foreman_config=foreman_config,
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        execution_count = {"count": 0}

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            async def track_execution(message):
                execution_count["count"] += 1
                await asyncio.sleep(0.1)
                return f"Response {execution_count['count']}"

            mock_session.execute = AsyncMock(side_effect=track_execution)

            mock_context = AsyncMock()
            mock_session.coordinator = MagicMock()
            mock_session.coordinator.get = MagicMock(return_value=mock_context)

            mock_session_class.return_value = mock_session

            async with orchestrator:
                # Send multiple messages concurrently
                results = await asyncio.gather(
                    orchestrator.execute_user_message("Message 1"),
                    orchestrator.execute_user_message("Message 2"),
                    orchestrator.execute_user_message("Message 3"),
                )

                # All should complete
                assert len(results) == 3
                assert execution_count["count"] == 3

    @pytest.mark.asyncio
    async def test_shutdown_during_message_execution(
        self, mock_loader: MagicMock, foreman_config: dict, workspace_dir: Path
    ):
        """Test shutdown while foreman is processing a message."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            foreman_config=foreman_config,
            worker_configs=[],
            workspace_root=workspace_dir,
        )

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            async def slow_execution(message):
                await asyncio.sleep(0.5)
                return "Response"

            mock_session.execute = AsyncMock(side_effect=slow_execution)

            mock_context = AsyncMock()
            mock_session.coordinator = MagicMock()
            mock_session.coordinator.get = MagicMock(return_value=mock_context)

            mock_session_class.return_value = mock_session

            # Start message execution
            async def send_message():
                return await orchestrator.execute_user_message("Test")

            # Start shutdown after short delay
            async def delayed_shutdown():
                await asyncio.sleep(0.1)
                await orchestrator.shutdown()

            # Both should complete without hanging
            message_task = asyncio.create_task(send_message())
            shutdown_task = asyncio.create_task(delayed_shutdown())

            await asyncio.wait([message_task, shutdown_task], timeout=2.0)

            # Should complete (either message finishes or gets interrupted)
            assert shutdown_task.done()


class TestWorkerErrorHandling:
    """Test worker error handling and recovery."""

    @pytest.mark.asyncio
    async def test_worker_error_doesnt_crash_orchestrator(
        self, mock_loader: MagicMock, foreman_config: dict, coding_worker_config: dict, workspace_dir: Path
    ):
        """Test worker errors don't crash the orchestrator."""
        worker_configs = [WorkerConfig(name="coding-worker", config=coding_worker_config, count=1)]

        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            foreman_config=foreman_config,
            worker_configs=worker_configs,
            workspace_root=workspace_dir,
        )

        error_count = {"count": 0}

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            mock_context = AsyncMock()

            def create_foreman_session(config, **kwargs):
                session = AsyncMock()
                session.__aenter__ = AsyncMock(return_value=session)
                session.__aexit__ = AsyncMock()
                session.execute = AsyncMock(return_value="Response")
                session.coordinator = MagicMock()
                session.coordinator.get = MagicMock(return_value=mock_context)
                return session

            def create_worker_session(config, **kwargs):
                session = AsyncMock()
                session.__aenter__ = AsyncMock(return_value=session)
                session.__aexit__ = AsyncMock()

                async def failing_execute(prompt):
                    error_count["count"] += 1
                    if error_count["count"] == 1:
                        raise RuntimeError("Worker error")
                    return "no work"

                session.execute = AsyncMock(side_effect=failing_execute)
                session.coordinator = MagicMock()
                session.coordinator.get = MagicMock(return_value=mock_context)
                return session

            def session_factory(config, **kwargs):
                # Check if this is foreman by looking at config structure
                # Foreman config has been loaded from file at this point
                if isinstance(config, dict) and config.get("tools", {}).get("issue_manager"):
                    # Check if it has the foreman profile indicators
                    # For simplicity, track which session is being created
                    if not hasattr(session_factory, "foreman_created"):
                        session_factory.foreman_created = True
                        return create_foreman_session(config, **kwargs)
                return create_worker_session(config, **kwargs)

            mock_session_class.side_effect = session_factory

            async with orchestrator:
                # Should initialize successfully
                response = await orchestrator.execute_user_message("Test")
                assert response == "Response"

                # Give worker time to fail and recover
                await asyncio.sleep(0.3)

                # Worker should still be running (recovered from error)
                assert len(orchestrator.worker_tasks) == 1
                assert error_count["count"] >= 1  # Had at least one error

    @pytest.mark.asyncio
    async def test_worker_continues_after_no_work(
        self, mock_loader: MagicMock, foreman_config: dict, coding_worker_config: dict, workspace_dir: Path
    ):
        """Test worker continues polling after finding no work."""
        worker_configs = [WorkerConfig(name="coding-worker", config=coding_worker_config, count=1)]

        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            foreman_config=foreman_config,
            worker_configs=worker_configs,
            workspace_root=workspace_dir,
        )

        poll_count = {"count": 0}

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession") as mock_session_class:
            foreman_session = AsyncMock()
            foreman_session.__aenter__ = AsyncMock(return_value=foreman_session)
            foreman_session.__aexit__ = AsyncMock()
            foreman_session.execute = AsyncMock(return_value="Response")

            worker_session = AsyncMock()
            worker_session.__aenter__ = AsyncMock(return_value=worker_session)
            worker_session.__aexit__ = AsyncMock()

            async def track_polls(prompt):
                poll_count["count"] += 1
                return "no work available"

            worker_session.execute = AsyncMock(side_effect=track_polls)

            mock_context = AsyncMock()
            foreman_session.coordinator = MagicMock()
            foreman_session.coordinator.get = MagicMock(return_value=mock_context)
            worker_session.coordinator = MagicMock()
            worker_session.coordinator.get = MagicMock(return_value=mock_context)

            def session_factory(config, **kwargs):
                if "foreman" in str(config):
                    return foreman_session
                return worker_session

            mock_session_class.side_effect = session_factory

            async with orchestrator:
                await orchestrator.execute_user_message("Test")

                # Let worker poll multiple times
                await asyncio.sleep(0.3)

            # Worker should have polled multiple times
            assert poll_count["count"] >= 2


class TestEmptyConfigurations:
    """Test handling of empty or minimal configurations."""

    @pytest.mark.asyncio
    async def test_zero_workers(self, mock_loader: MagicMock, foreman_config: dict, workspace_dir: Path):
        """Test orchestrator with zero workers."""
        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            foreman_config=foreman_config,
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

            async with orchestrator:
                response = await orchestrator.execute_user_message("Test")

                assert response == "Response"
                assert len(orchestrator.worker_tasks) == 0

    @pytest.mark.asyncio
    async def test_worker_with_zero_count(
        self, mock_loader: MagicMock, foreman_config: dict, coding_worker_config: dict, workspace_dir: Path
    ):
        """Test worker config with count=0."""
        worker_configs = [WorkerConfig(name="coding-worker", config=coding_worker_config, count=0)]

        orchestrator = ForemanWorkerOrchestrator(
            loader=mock_loader,
            foreman_config=foreman_config,
            worker_configs=worker_configs,
            workspace_root=workspace_dir,
        )

        with patch("amplifier_orchestrator_foreman_worker.orchestrator.AmplifierSession"):
            await orchestrator._start_workers()

            assert len(orchestrator.worker_tasks) == 0
