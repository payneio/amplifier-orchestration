"""Observer Orchestrator - Bottom-up feedback pattern.

This orchestrator implements the observer pattern where:
- A main session does actual work (creating content, writing code, etc.)
- Observer sessions watch the output and create feedback issues
- The main session addresses feedback in iterative rounds
- The process converges when observers have no more feedback

This is the inverse of the foreman-worker pattern:
- Foreman-Worker: Top-down delegation (foreman creates tasks for workers)
- Observer: Bottom-up feedback (observers create issues for main to address)
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from amplifier_core import AmplifierSession, ModuleLoader

from .config import ObserverConfig

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ObserverOrchestrator:
    """Orchestrates a main session with observer feedback loops.

    The main session does actual work while observer sessions watch and
    provide feedback through the issue system. This enables iterative
    refinement through autonomous critique.

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
            # Initial work
            response = await orchestrator.execute_user_message("Research topic X")

            # Run feedback rounds
            for round_num in range(3):
                issues = await orchestrator.run_observer_round(round_num + 1)
                if issues == 0:
                    break
                await orchestrator.address_feedback(round_num + 1)
    """

    def __init__(
        self,
        loader: ModuleLoader,
        main_config: dict,
        observer_configs: list[ObserverConfig],
        workspace_root: Path,
        approval_system: Any = None,
        display_system: Any = None,
    ):
        """Initialize the observer orchestrator.

        Args:
            loader: Amplifier module loader
            main_config: Mount plan configuration for the main session
            observer_configs: List of observer configurations
            workspace_root: Root workspace directory
            approval_system: Optional approval system for tool calls
            display_system: Optional display system for UI messages
        """
        self.loader = loader
        self.main_config = main_config
        self.observer_configs = observer_configs
        self.workspace_root = workspace_root
        self.approval_system = approval_system
        self.display_system = display_system

        # Runtime state (initialized lazily)
        self.main_session: AmplifierSession | None = None
        self._initialized = False
        self._shutdown_event = asyncio.Event()

    async def __aenter__(self) -> "ObserverOrchestrator":
        """Enter async context manager."""
        return self

    async def __aexit__(self, *_args: Any) -> None:
        """Exit async context manager, ensuring cleanup."""
        await self.shutdown()

    async def _initialize(self) -> None:
        """Initialize the main session (called on first message)."""
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
watch your output and provide feedback through issues.

## Observers Watching You
{observer_list}

## How This Works
1. You receive tasks from the user and execute them
2. Observers review your output and create issues for improvements
3. You should periodically check for open issues using the issue tool
4. Address feedback issues by improving your work
5. Close issues when you've addressed the feedback

## Issue Workflow
- Use `list_issues` with status=open to see feedback
- Read each issue's description for specific feedback
- Update your work to address the concern
- Close the issue with a note about what you changed

## Focus
- Do your primary work first
- When asked to address feedback, check for open issues
- Address issues thoughtfully, improving quality
- Work iteratively - observers may have follow-up feedback
"""

    async def execute_user_message(self, message: str) -> str:
        """Execute a user message through the main session.

        This handles initial work requests and feedback addressing.

        Args:
            message: The user's message

        Returns:
            The main session's response
        """
        await self._initialize()

        if self.main_session is None:
            raise RuntimeError("Main session not initialized")

        logger.info("Executing user message through main session")

        # Use hybrid async approach to ensure fair scheduling
        # (same pattern as work-coordinator)
        task = asyncio.create_task(self.main_session.execute(message))

        while not task.done():
            await asyncio.sleep(0.1)

        return await task

    async def run_observer_round(self, round_num: int) -> int:
        """Run all observers for a feedback round.

        Each observer reviews the current state and creates issues
        for problems in their domain.

        Args:
            round_num: The current round number (for context)

        Returns:
            Total number of issues created across all observers
        """
        if not self._initialized or self.main_session is None:
            raise RuntimeError("Orchestrator not initialized")

        logger.info(f"Running observer round {round_num}")

        # Get main session ID for parent linking
        main_session_id = getattr(self.main_session, "session_id", None)

        # Run all observers in parallel
        tasks = [
            asyncio.create_task(
                self._run_single_observer(obs, round_num, main_session_id)
            )
            for obs in self.observer_configs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count total issues created
        total_issues = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Observer {self.observer_configs[i].name} failed: {result}")
            elif isinstance(result, int):
                total_issues += result

        logger.info(f"Observer round {round_num} complete: {total_issues} issues created")
        return total_issues

    async def _run_single_observer(
        self,
        observer: ObserverConfig,
        round_num: int,
        parent_session_id: str | None,
    ) -> int:
        """Run a single observer's review.

        Args:
            observer: The observer configuration
            round_num: Current round number
            parent_session_id: Main session ID for linking

        Returns:
            Number of issues created (0-2 typically)
        """
        logger.info(f"Observer {observer.name} starting review")

        # Deep copy config to modify actor
        import json
        config = json.loads(json.dumps(observer.config))
        for tool in config.get("tools", []):
            if tool.get("module") == "tool-issue":
                tool["config"]["actor"] = observer.name.lower().replace(" ", "-")

        try:
            async with AmplifierSession(
                config,
                loader=self.loader,
                parent_id=parent_session_id,
                approval_system=self.approval_system,
                display_system=self.display_system,
            ) as session:
                # Inject observer instructions
                instructions = self._build_observer_instructions(observer, round_num)
                context = session.coordinator.get("context")
                if not context:
                    raise RuntimeError(f"Observer {observer.name}: No context manager mounted")
                await context.add_message({"role": "system", "content": instructions})

                # Execute review
                prompt = f"""Review the current work for round {round_num}.

1. Read any relevant files in the work directory
2. Analyze from your specialized perspective: {observer.role}
3. If you find issues, create them using the issue tool
4. Create at most 2 issues (focus on the most important)
5. If everything looks good from your perspective, say "No issues found"

Focus: {observer.focus}"""

                result = await session.execute(prompt)

                # Estimate issues created (heuristic)
                if "no issues" in result.lower() or "looks good" in result.lower():
                    return 0

                # Count mentions of issue creation
                issues = min(result.lower().count("created"), 2)
                return max(issues, 1) if "issue" in result.lower() else 0

        except Exception as e:
            logger.error(f"Observer {observer.name} error: {e}")
            raise

    def _build_observer_instructions(self, observer: ObserverConfig, round_num: int) -> str:
        """Build system instructions for an observer session."""
        return f"""You are **{observer.name}**, a specialized observer/reviewer.

## Your Role
{observer.role}

## Your Focus
{observer.focus}

## Review Guidelines for Round {round_num}
1. Read the work files to understand current state
2. Analyze strictly from your specialized perspective
3. Create issues ONLY for problems in your domain
4. Each issue should have:
   - Clear, specific title
   - Detailed description with suggestion for improvement
   - Metadata: {{"observer": "{observer.name}", "round": {round_num}}}
5. Create at most 2 issues per round (prioritize)
6. Don't repeat issues from previous rounds
7. If work is good from your perspective, say "No issues found"

## Issue Creation
Use type="task", priority=2 for feedback issues.
Be specific about what's wrong and how to improve it.
"""

    async def address_feedback(self, round_num: int) -> bool:
        """Have the main session address open feedback issues.

        Args:
            round_num: Current round number

        Returns:
            True if there was feedback to address, False if no open issues
        """
        if not self._initialized or self.main_session is None:
            raise RuntimeError("Orchestrator not initialized")

        logger.info(f"Addressing feedback for round {round_num}")

        prompt = f"""Check for and address feedback from observers (Round {round_num}).

1. Use the issue tool to list all open issues (status=open)
2. For each issue:
   - Read the feedback carefully
   - Update your work to address the concern
   - Close the issue with a note about what you changed
3. If there are no open issues, respond with "No feedback to address"

Address all feedback thoughtfully to improve quality."""

        result = await self.main_session.execute(prompt)

        no_feedback = (
            "no feedback" in result.lower()
            or "no open issues" in result.lower()
            or "no issues" in result.lower()
        )

        return not no_feedback

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

        # Close main session
        if self.main_session is not None:
            await self.main_session.__aexit__(None, None, None)
            self.main_session = None

        self._initialized = False
        logger.info("Observer orchestrator shutdown complete")
