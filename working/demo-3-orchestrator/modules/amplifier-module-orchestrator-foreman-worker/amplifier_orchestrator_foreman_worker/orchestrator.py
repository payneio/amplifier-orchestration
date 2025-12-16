"""Foreman-Worker orchestrator implementation."""

import asyncio
import logging
from pathlib import Path
from typing import Any

from amplifier_core import AmplifierSession
from amplifier_core import ModuleLoader

from .config import WorkerConfig

logger = logging.getLogger(__name__)


class ForemanWorkerOrchestrator:
    """Orchestrator implementing foreman-worker pattern.

    The foreman handles user messages (request-response).
    Workers run in continuous background loops (autonomous).

    Args:
        loader: Module loader for Amplifier components
        foreman_config: Mount plan configuration for the foreman
        worker_configs: List of worker configurations (name, config, count)
        workspace_root: Root directory for workspace operations

    Example:
        >>> workers = [
        ...     WorkerConfig(name="coding-worker", config=coding_config, count=2),
        ...     WorkerConfig(name="research-worker", config=research_config, count=1),
        ... ]
        >>> async with ForemanWorkerOrchestrator(
        ...     loader=loader,
        ...     foreman_config=foreman_config,
        ...     worker_configs=workers,
        ...     workspace_root=Path("workspace")
        ... ) as orchestrator:
        ...     response = await orchestrator.execute_user_message("Build a scraper")
        ...     print(response)
    """

    def __init__(
        self,
        loader: ModuleLoader,
        foreman_config: dict,
        worker_configs: list[WorkerConfig],
        workspace_root: Path,
        approval_system: Any = None,
        display_system: Any = None,
    ):
        self.loader = loader
        self.foreman_config = foreman_config
        self.worker_configs = worker_configs
        self.workspace_root = workspace_root
        self.approval_system = approval_system
        self.display_system = display_system

        # Runtime state (initialized lazily)
        self.foreman_session: AmplifierSession | None = None
        self.worker_tasks: list[asyncio.Task] = []
        self.worker_session_ids: dict[str, str] = {}  # worker_id -> session_id
        self._shutdown_event = asyncio.Event()
        self._initialized = False

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, *_args):
        """Context manager exit - ensure clean shutdown."""
        await self.shutdown()

    async def execute_user_message(self, message: str) -> str:
        """Execute user message through foreman.

        Initializes foreman and workers on first call.

        Args:
            message: User message to process

        Returns:
            Foreman's response to the message

        Raises:
            RuntimeError: If initialization or execution fails

        Note:
            Uses explicit yield points to ensure background worker tasks get CPU time.
            See implementation comments for details on event loop fairness.
        """
        # Lazy initialization on first message
        if not self._initialized:
            await self._initialize()

        # Process message through foreman
        if not self.foreman_session:
            raise RuntimeError("Foreman session not initialized")

        try:
            # HYBRID ASYNC APPROACH: Explicit Yield Points for Event Loop Fairness
            #
            # Problem: Python's event loop is cooperative - long-running await calls
            # (like LLM requests taking 3-6 seconds) don't automatically yield to other
            # tasks. This causes "event loop starvation" where background worker tasks
            # never get CPU time to poll for and claim issues.
            #
            # Solution: Instead of directly awaiting foreman execution (which blocks),
            # we create a background task and poll it with explicit yield points.
            # This gives worker tasks regular opportunities to execute.
            #
            # Technical Details:
            # - Direct await: await session.execute(message)
            #   → Blocks for entire 3-6s LLM response time
            #   → Workers get 0 CPU time during this period
            #
            # - Hybrid approach: Create task + yield every 100ms
            #   → Foreman task runs in background
            #   → Yields every 100ms give workers CPU time
            #   → During a 3s foreman execution, workers get ~30 opportunities to run
            #
            # Why 100ms?
            # - Fast enough for responsive workers (10 yields per second)
            # - Slow enough to avoid excessive context switching overhead
            # - Good balance between fairness and efficiency
            #
            # Alternative considered: Making foreman a background task with message queues
            # - Would work but adds significant complexity (queues, task management)
            # - This approach achieves 95% of benefits with 5% of complexity
            # - Follows "ruthless simplicity" philosophy

            # Create foreman execution as a background task
            execution_task = asyncio.create_task(
                self.foreman_session.execute(message)
            )

            # Poll with explicit yields to give worker tasks CPU time
            while not execution_task.done():
                # Yield control to event loop every 100ms
                # This allows worker tasks to:
                # - Poll for new issues
                # - Claim available work
                # - Complete tasks
                await asyncio.sleep(0.1)

            # Task is complete, retrieve and return result
            response = execution_task.result()
            return response

        except Exception as e:
            logger.error(f"Error executing foreman message: {e}")
            raise RuntimeError(f"Foreman execution failed: {e}") from e

    async def _initialize(self):
        """Initialize foreman and workers."""
        logger.info("Initializing foreman-worker orchestrator")

        # Create foreman session
        self.foreman_session = AmplifierSession(
            config=self.foreman_config,
            loader=self.loader,
            approval_system=self.approval_system,
            display_system=self.display_system,
        )

        # Enter foreman session context
        await self.foreman_session.__aenter__()

        # Inject system instructions directly into context manager
        context = self.foreman_session.coordinator.get("context")
        if not context:
            raise RuntimeError("Foreman: No context manager mounted")

        foreman_instructions = (
            "You are the Foreman. Handle user requests by delegating work to workers.\n\n"
            "You have access to the issue_manager tool to create and manage work items.\n\n"
            "IMPORTANT - Issue Status Values:\n"
            "- 'open': Unassigned work waiting for workers\n"
            "- 'in_progress': Currently being worked on\n"
            "- 'pending_user_input': Worker needs information from the user (YOU must ask!)\n"
            "- 'blocked': Blocked by another task dependency\n"
            "- 'closed': Completed work (when users ask about 'completed' issues, use status='closed')\n\n"
            "CRITICAL - USER INPUT WORKFLOW:\n"
            "When checking status, ALWAYS look for 'pending_user_input' issues!\n"
            "- Workers use 'request_user_input' operation when they need info from the user\n"
            "- The blocking_notes field explains what information is needed\n"
            "- YOU must ask the user for that info\n"
            "- When user provides info, use 'unblock' operation:\n"
            "  issue_manager operation='unblock' issue_id=<id> info='<user provided info>'\n"
            "- This sets status back to 'open' so workers can continue\n\n"
            "When creating issues:\n"
            "- issue_type MUST be one of: 'bug', 'feature', 'task', 'epic', 'chore'\n"
            "- For CODING tasks: use issue_type='bug' or 'feature', AND metadata={'category': 'coding'}\n"
            "- For RESEARCH tasks: use issue_type='task', AND metadata={'category': 'research'}\n\n"
            "CRITICAL: Every issue MUST have:\n"
            "1. A valid issue_type (bug/feature/task/epic/chore)\n"
            "2. metadata.category set to 'coding' or 'research' so workers can find their work!\n\n"
            "SEMANTIC OPERATIONS (preferred - use these!):\n"
            "- unblock: Resume an issue after user provides info\n"
            "- complete: Finish work on an issue (closes it)\n\n"
            "Use tools proactively to:\n"
            "- Create issues for work delegation\n"
            "- Check for 'pending_user_input' issues and ask user for needed info\n"
            "- Use 'unblock' when user provides the requested info\n"
            "- Check issue status (remember: completed work has status='closed')\n"
            "- Review completed work\n\n"
            "Review completed work and respond to user requests."
        )

        await context.add_message({"role": "system", "content": foreman_instructions})
        logger.info("Foreman session started with system instructions")

        # Start all workers
        await self._start_workers()

        self._initialized = True
        logger.info("Foreman-worker orchestrator initialized")

    async def _start_workers(self):
        """Spawn worker background tasks."""
        logger.info("_start_workers() called - beginning worker initialization")
        worker_id_counter = 0

        for worker_config in self.worker_configs:
            logger.info(f"Processing worker_config: {worker_config.name}, count={worker_config.count}")
            for _ in range(worker_config.count):
                worker_id = f"{worker_config.name}-{worker_id_counter}"
                worker_id_counter += 1
                logger.info(f"Creating task for worker: {worker_id}")

                task = asyncio.create_task(
                    self._worker_loop(worker_id, worker_config.name, worker_config.config),
                    name=worker_id,
                )
                self.worker_tasks.append(task)
                logger.info(f"Started worker: {worker_id}")

        logger.info(f"Started {len(self.worker_tasks)} workers - tasks created")

    async def _worker_loop(self, worker_id: str, worker_name: str, config: dict):
        """Worker continuous processing loop.

        Workers claim tasks and complete them in an infinite loop
        until shutdown is signaled.

        Args:
            worker_id: Unique identifier for this worker
            worker_name: Worker type name (e.g., "coding-worker")
            config: Mount plan configuration dictionary
        """
        logger.info(f"_worker_loop() ENTERED for {worker_id}")
        try:
            # Determine worker category from name
            worker_category = "coding" if "coding" in worker_name else "research" if "research" in worker_name else "general"

            # Create worker session with foreman as parent
            foreman_session_id = self.foreman_session.session_id if self.foreman_session else None
            async with AmplifierSession(
                config,
                loader=self.loader,
                parent_id=foreman_session_id,
                approval_system=self.approval_system,
                display_system=self.display_system,
            ) as session:
                # Track worker session ID
                self.worker_session_ids[worker_id] = session.session_id
                logger.info(f"Worker {worker_id} session: {session.session_id}")

                # Inject system instructions directly into context manager
                context = session.coordinator.get("context")
                if not context:
                    raise RuntimeError(f"Worker {worker_id}: No context manager mounted")

                system_instructions = (
                    f"You are {worker_id}, a {worker_category} worker.\n\n"
                    "CRITICAL EXECUTION RULES:\n"
                    "1. You MUST use tools to do ALL work - never respond without tools\n"
                    "2. You MUST complete the ENTIRE workflow in ONE execution cycle\n"
                    "3. DO NOT stop after just listing issues - that's only step 1\n"
                    "4. DO NOT respond to explain what you're doing - just DO it\n"
                    "5. Continue calling tools until work is COMPLETE\n\n"
                    "Available Tools:\n"
                    "- issue_manager: Manage work items and track progress\n"
                    "- read_file, write_file, edit_file: File operations for doing work\n"
                    "- bash: Execute commands if needed\n\n"
                    "COMPLETE WORKFLOW (execute ALL steps in single turn):\n\n"
                    "STEP 1: List YOUR open issues using metadata filter\n"
                    f"   → issue_manager operation='list' status='open' metadata={{{{'category': '{worker_category}'}}}}\n\n"
                    f"STEP 2: If you got issues from step 1, pick one\n"
                    f"   → You've already filtered by category, so any issue returned is YOUR work\n\n"
                    f"STEP 3: Claim the issue (use semantic operation)\n"
                    f"   → issue_manager operation='claim' issue_id=<id> assignee='{worker_id}'\n\n"
                    "STEP 4: Do the work\n"
                    "   → Use read_file, write_file, edit_file, bash as needed\n"
                    "   → Create files in 'work/' directory\n"
                    "   → Actually implement what the issue describes\n\n"
                    "STEP 5A: If the issue REQUIRES information from the user:\n"
                    "   → DO NOT make up or invent the required information!\n"
                    "   → Use the request_user_input operation:\n"
                    f"     issue_manager operation='request_user_input' issue_id=<id> reason='<what you need>'\n"
                    "   → The foreman will ask the user and unblock the issue when info is provided\n"
                    "   → Respond: 'Waiting for user input on <issue title>'\n\n"
                    "STEP 5B: If work is COMPLETE (all requirements satisfied):\n"
                    "   → issue_manager operation='complete' issue_id=<id> reason='Work completed'\n\n"
                    f"STEP 6: If NO {worker_category} issues found in step 1\n"
                    "   → Respond EXACTLY: 'no work'\n\n"
                    "SEMANTIC OPERATIONS (preferred - use these!):\n"
                    "- claim: Start working on an issue (sets in_progress + assignee)\n"
                    "- request_user_input: Ask user for info (sets pending_user_input)\n"
                    "- complete: Finish work on an issue (closes it)\n"
                    "- release: Stop working, put back in queue (if needed)\n\n"
                    "EXECUTION RULES:\n"
                    "- Execute ALL steps in sequence during THIS turn\n"
                    "- Use multiple tool calls as needed - don't stop early\n"
                    "- Only respond with text AFTER completing work OR if no work found\n"
                    "- If you find work, you MUST complete it before responding\n\n"
                    "FORBIDDEN:\n"
                    "- DO NOT respond with just the list of issues\n"
                    "- DO NOT explain what you're about to do\n"
                    "- DO NOT wait for confirmation before claiming/completing work\n"
                    "- DO NOT stop after any single step - complete the entire workflow\n"
                    "- DO NOT invent or make up information that the user should provide"
                )
                # NOTE: Removed .format() call - string already uses f-strings for all variables

                await context.add_message({"role": "system", "content": system_instructions})
                logger.info(f"Worker {worker_id} started with system instructions")

                while not self._shutdown_event.is_set():
                    try:
                        # Ultra-explicit prompt to ensure complete workflow execution
                        # NOTE: Now uses metadata filtering directly in the tool call
                        # for reliable issue discovery (no manual parsing needed)
                        prompt = f"""You are {worker_id}, a {worker_category} worker.

Task: Find and work on one issue

1. List YOUR issues:
   issue_manager operation='list' status='open' metadata={{'category': '{worker_category}'}}

2. If you find one, use SEMANTIC OPERATIONS:
   - CLAIM it: issue_manager operation='claim' issue_id=<id> assignee='{worker_id}'
   - Do the work (read_file, write_file, etc.)
   - IF you need user info: issue_manager operation='request_user_input' issue_id=<id> reason='<what you need>'
   - IF work complete: issue_manager operation='complete' issue_id=<id> reason='Done'

3. If no issues available, respond with "No work available"

Process ONE issue then stop."""

                        result = await session.execute(prompt)

                        # Log actual response to debug what workers are doing
                        logger.info(f"Worker {worker_id} response: {result[:300]}")

                        if "no work" in result.lower():
                            logger.debug(f"Worker {worker_id}: no work available")
                        else:
                            logger.info(f"Worker {worker_id}: completed task")

                        # Delay between cycles - accounts for multi-step workflows
                        # Each cycle can involve 2-4 API calls (3-6 seconds each)
                        await asyncio.sleep(5)

                    except Exception as e:
                        logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
                        # Longer delay on error to avoid error loops
                        await asyncio.sleep(5)

                logger.info(f"Worker {worker_id} shutting down")

        except Exception:
            logger.error(f"Worker {worker_id} failed to initialize", exc_info=True)
            raise

    async def shutdown(self):
        """Shutdown orchestrator cleanly.

        Signals workers to stop, waits for completion, and closes sessions.
        """
        if not self._initialized:
            return

        logger.info("Shutting down foreman-worker orchestrator")

        # Signal workers to stop
        self._shutdown_event.set()

        # Wait for workers to complete
        if self.worker_tasks:
            logger.info(f"Waiting for {len(self.worker_tasks)} workers to stop...")
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
            logger.info("All workers stopped")

        # Close foreman session
        if self.foreman_session:
            await self.foreman_session.__aexit__(None, None, None)
            logger.info("Foreman session closed")

        self._initialized = False
        logger.info("Shutdown complete")
