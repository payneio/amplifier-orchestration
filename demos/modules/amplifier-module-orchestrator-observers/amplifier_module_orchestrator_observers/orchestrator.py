"""Observer Orchestrator - Bottom-up feedback pattern with continuous observers.

This orchestrator implements the observer pattern where:
- A main session does actual work (creating content, writing code, etc.)
- Observer sessions run continuously in background, watching for changes
- When observers spot issues, they create feedback issues autonomously
- The main session can address feedback between user interactions

This is the inverse of the foreman-worker pattern:
- Foreman-Worker: Top-down delegation (foreman creates tasks for workers)
- Observer: Bottom-up feedback (observers watch and create issues autonomously)

Like foreman-worker, observers run in continuous background loops - no manual
round management needed. The demo/app just sends messages to the main session
and observers automatically provide feedback.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from amplifier_core import AmplifierSession, ModuleLoader

from .config import ObserverConfig

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ObserverOrchestrator:
    """Orchestrates a main session with continuous background observers.

    Observers run in infinite loops (like workers in foreman-worker pattern),
    automatically watching for changes and creating feedback issues. The main
    session handles user messages and can optionally auto-address feedback.

    Usage:
        async with ObserverOrchestrator(
            loader=loader,
            main_config=main_config,
            observer_configs=[
                ObserverConfig(
                    name="skeptic",
                    config=observer_config,
                    role="Questions unsupported claims",
                    focus="Look for claims lacking evidence..."
                ),
            ],
            workspace_root=workspace,
        ) as orchestrator:
            # Observers start automatically in background
            response = await orchestrator.execute_user_message("Research topic X")
            # Observers are watching and creating issues as needed
            # Wait for work to settle, then get final result
            await asyncio.sleep(30)
            final = await orchestrator.execute_user_message("Address any feedback")
    """

    def __init__(
        self,
        loader: ModuleLoader,
        main_config: dict,
        observer_configs: list[ObserverConfig],
        workspace_root: Path,
        approval_system: Any = None,
        display_system: Any = None,
        observer_interval: float = 15.0,  # Seconds between observer checks
        watch_paths: list[str] | None = None,  # Paths to watch for changes
    ):
        """Initialize the observer orchestrator.

        Args:
            loader: Amplifier module loader
            main_config: Mount plan configuration for the main session
            observer_configs: List of observer configurations
            workspace_root: Root workspace directory
            approval_system: Optional approval system for tool calls
            display_system: Optional display system for UI messages
            observer_interval: Seconds between observer review cycles
            watch_paths: File paths observers should watch (e.g., ["work/"])
        """
        self.loader = loader
        self.main_config = main_config
        self.observer_configs = observer_configs
        self.workspace_root = workspace_root
        self.approval_system = approval_system
        self.display_system = display_system
        self.observer_interval = observer_interval
        self.watch_paths = watch_paths or ["work/"]

        # Runtime state (initialized lazily)
        self.main_session: AmplifierSession | None = None
        self.observer_tasks: list[asyncio.Task] = []
        self.observer_session_ids: dict[str, str] = {}
        self._initialized = False
        self._shutdown_event = asyncio.Event()

    async def __aenter__(self) -> "ObserverOrchestrator":
        """Enter async context manager."""
        return self

    async def __aexit__(self, *_args: Any) -> None:
        """Exit async context manager, ensuring cleanup."""
        await self.shutdown()

    async def _initialize(self) -> None:
        """Initialize the main session and start observers (called on first message)."""
        if self._initialized:
            return

        logger.info("Initializing observer orchestrator")

        # Create and enter main session
        self.main_session = AmplifierSession(
            config=self.main_config,
            loader=self.loader,
            approval_system=self.approval_system,
            display_system=self.display_system,
        )
        await self.main_session.__aenter__()

        # Inject system instructions for the main session
        main_instructions = self._build_main_instructions()
        context = self.main_session.coordinator.get("context")
        if not context:
            raise RuntimeError("Main session: No context manager mounted")
        await context.add_message({"role": "system", "content": main_instructions})

        # Start all observer background loops
        await self._start_observers()

        self._initialized = True
        logger.info("Observer orchestrator initialized")

    def _build_main_instructions(self) -> str:
        """Build system instructions for the main session."""
        observer_list = "\n".join(
            f"- **{obs.name}**: {obs.role}" for obs in self.observer_configs
        )

        return f"""You are the main working session in an observer-feedback system.

## Your Role
You do actual work (research, coding, writing, etc.) while observer sessions
run in the background, watching your output and providing feedback through issues.

## Observers Watching You
{observer_list}

## How This Works
1. You receive tasks from the user and execute them
2. Observers continuously monitor your work and create issues for improvements
3. When asked to "address feedback" or "check for issues", use the issue tool
4. Address feedback issues by improving your work and closing them

## Issue Workflow
- Use `list_issues` with status=open to see feedback from observers
- Read each issue's description for specific feedback
- Update your work to address the concern
- Close the issue with a note about what you changed

## Focus
- Do your primary work when given tasks
- When asked to address feedback, check for and resolve open issues
- Work iteratively - observers may provide ongoing feedback
"""

    async def _start_observers(self) -> None:
        """Start all observer background loops."""
        logger.info("Starting observer background loops")

        for observer in self.observer_configs:
            task = asyncio.create_task(
                self._observer_loop(observer),
                name=f"observer-{observer.name}",
            )
            self.observer_tasks.append(task)
            logger.info(f"Started observer: {observer.name}")

        logger.info(f"Started {len(self.observer_tasks)} observers")

    async def _observer_loop(self, observer: ObserverConfig) -> None:
        """Continuous observer loop - watches and creates feedback.

        Runs until shutdown, periodically reviewing work and creating
        issues when problems are spotted.
        """
        logger.info(f"Observer {observer.name} starting continuous loop")

        # Track what we've reviewed to avoid duplicate feedback
        last_review_state: str | None = None

        # Deep copy config to modify actor
        config = json.loads(json.dumps(observer.config))
        for tool in config.get("tools", []):
            if tool.get("module") == "tool-issue":
                tool["config"]["actor"] = observer.name.lower().replace(" ", "-")

        # Get main session ID for parent linking
        main_session_id = getattr(self.main_session, "session_id", None) if self.main_session else None

        while not self._shutdown_event.is_set():
            try:
                # Check if there's work to review
                current_state = await self._get_work_state()

                if current_state and current_state != last_review_state:
                    logger.info(f"Observer {observer.name}: Detected changes, reviewing...")

                    # Create a session for this review cycle
                    async with AmplifierSession(
                        config,
                        loader=self.loader,
                        parent_id=main_session_id,
                        approval_system=self.approval_system,
                        display_system=self.display_system,
                    ) as session:
                        # Track session ID
                        self.observer_session_ids[observer.name] = getattr(session, "session_id", "unknown")

                        # Inject observer instructions
                        instructions = self._build_observer_instructions(observer)
                        context = session.coordinator.get("context")
                        if context:
                            await context.add_message({"role": "system", "content": instructions})

                        # Execute review
                        prompt = self._build_review_prompt(observer)
                        await session.execute(prompt)

                    last_review_state = current_state
                    logger.info(f"Observer {observer.name}: Review complete")

            except asyncio.CancelledError:
                logger.info(f"Observer {observer.name}: Cancelled")
                break
            except Exception as e:
                logger.error(f"Observer {observer.name} error: {e}")
                # Continue running despite errors

            # Wait before next check
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.observer_interval,
                )
                # If we get here, shutdown was signaled
                break
            except asyncio.TimeoutError:
                # Normal timeout, continue loop
                pass

        logger.info(f"Observer {observer.name}: Loop ended")

    async def _get_work_state(self) -> str | None:
        """Get a hash/signature of the current work state.

        Returns a string representing the current state of watched files,
        or None if no work exists yet.
        """
        state_parts = []

        for watch_path in self.watch_paths:
            path = Path(watch_path)
            if not path.is_absolute():
                path = Path.cwd() / path

            if path.exists():
                if path.is_file():
                    stat = path.stat()
                    state_parts.append(f"{path}:{stat.st_mtime}:{stat.st_size}")
                elif path.is_dir():
                    for file in path.rglob("*"):
                        if file.is_file():
                            stat = file.stat()
                            state_parts.append(f"{file}:{stat.st_mtime}:{stat.st_size}")

        if not state_parts:
            return None

        # Sort for consistency
        state_parts.sort()
        return "|".join(state_parts)

    def _build_observer_instructions(self, observer: ObserverConfig) -> str:
        """Build system instructions for an observer session."""
        return f"""You are **{observer.name}**, a specialized observer/reviewer running in continuous background mode.

## Your Role
{observer.role}

## Your Focus
{observer.focus}

## Review Guidelines
1. Read the work files to understand current state
2. Analyze strictly from your specialized perspective
3. Create issues ONLY for problems in your domain
4. Each issue should have:
   - Clear, specific title
   - Detailed description with suggestion for improvement
   - Metadata: {{"observer": "{observer.name}"}}
5. Create at most 2 issues per review (prioritize the most important)
6. Check existing open issues first - don't create duplicates
7. If the work looks good from your perspective, don't create any issues

## Issue Creation
Use type="task", priority=2 for feedback issues.
Be specific about what's wrong and how to improve it.
"""

    def _build_review_prompt(self, observer: ObserverConfig) -> str:
        """Build the review prompt for an observer."""
        watch_paths_str = ", ".join(self.watch_paths)
        return f"""Review the current work in: {watch_paths_str}

1. First, list any existing open issues to avoid duplicates
2. Read the work files to understand the current state
3. Analyze from your specialized perspective: {observer.role}
4. If you find NEW issues (not already reported), create them
5. Focus on: {observer.focus}

Create at most 2 issues for the most important problems you find.
If everything looks good, just say "No new issues found."
"""

    async def execute_user_message(self, message: str) -> str:
        """Execute a user message through the main session.

        This handles user requests. Observers run automatically in background.

        Args:
            message: The user's message

        Returns:
            The main session's response
        """
        await self._initialize()

        if self.main_session is None:
            raise RuntimeError("Main session not initialized")

        logger.info("Executing user message through main session")

        # Use hybrid async approach to ensure fair scheduling with observers
        task = asyncio.create_task(self.main_session.execute(message))

        while not task.done():
            await asyncio.sleep(0.1)

        return await task

    @property
    def main_session_id(self) -> str | None:
        """Get the main session ID."""
        if self.main_session is None:
            return None
        return getattr(self.main_session, "session_id", None)

    async def shutdown(self) -> None:
        """Shutdown the orchestrator and cleanup resources."""
        logger.info("Shutting down observer orchestrator")
        self._shutdown_event.set()

        # Wait for all observer tasks to complete
        if self.observer_tasks:
            logger.info(f"Waiting for {len(self.observer_tasks)} observers to stop...")
            await asyncio.gather(*self.observer_tasks, return_exceptions=True)
            self.observer_tasks.clear()

        # Close main session
        if self.main_session is not None:
            await self.main_session.__aexit__(None, None, None)
            self.main_session = None

        self._initialized = False
        logger.info("Observer orchestrator shutdown complete")
