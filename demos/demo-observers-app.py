"""
Research Compiler with Fact-Checkers Demo

Demonstrates the Observer pattern where:
- A main Researcher session researches and writes content
- Observer sessions watch the output and create feedback issues
- The Researcher addresses feedback and refines the content

KEY PATTERN - Bottom-Up Feedback:
================================
Unlike the Foreman-Worker pattern (top-down delegation), this demo shows
bottom-up feedback where observers autonomously identify issues:

1. Researcher writes initial research on a topic
2. Observers (Skeptic, Depth Seeker, Clarity Editor) read the content
3. Observers create issues when they spot problems in their domain
4. Researcher sees issues and addresses them
5. Cycle continues until observers have no more feedback

Observer Types:
- Skeptic: Questions claims that seem unsupported or dubious
- Depth Seeker: Identifies areas that need more detail or exploration
- Clarity Editor: Flags confusing or unclear passages

This demonstrates observers as autonomous critics that improve quality
through continuous feedback, without direct coordination.
"""

import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path

from amplifier_core import AmplifierSession, ModuleLoader


# ANSI colors
class Color:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[35m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Suppress noisy loggers
for logger_name in [
    "httpcore",
    "httpx",
    "anthropic",
    "amplifier_core",
    "amplifier_module_loop_streaming",
    "amplifier_module_context_persistent",
    "amplifier_module_provider_anthropic",
    "amplifier_module_tool_filesystem",
    "amplifier_module_tool_bash",
    "amplifier_module_tool_issue",
    "amplifier_module_tool_web",
]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_module_search_paths() -> list[Path]:
    """Get module search paths for Amplifier Core."""
    modules_dir = Path(__file__).parent / "modules"
    if not modules_dir.exists():
        raise RuntimeError("Modules directory not found. Run setup:\n  python setup_modules.py")
    return [modules_dir]


def load_mount_plan(name: str) -> dict:
    """Load a mount plan from demo/mount_plans/"""
    mount_plan_path = Path(__file__).parent / "mount_plans" / f"{name}.json"
    with open(mount_plan_path) as f:
        return json.load(f)


# Demo configuration
RESEARCH_TOPIC = "the benefits and risks of intermittent fasting for health and longevity"
RESEARCH_FILE = "work/research.md"
MAX_ROUNDS = 3  # Maximum feedback rounds before stopping


async def researcher_initial_draft(loader: ModuleLoader, workspace: Path):
    """Researcher creates the initial research draft."""
    print(f"\n{Color.BLUE}{Color.BOLD}=== RESEARCHER: Creating Initial Draft ==={Color.ENDC}")

    config = load_mount_plan("researcher")

    async with AmplifierSession(config, loader=loader) as session:
        session_id = getattr(session, "session_id", "unknown")
        print(f"   Researcher session_id: {session_id}")

        prompt = f"""You are a research compiler. Your task is to research and write about:

**Topic: {RESEARCH_TOPIC}**

Instructions:
1. Research this topic thoroughly (you can use web search if available)
2. Write a comprehensive research summary to the file: {RESEARCH_FILE}
3. Include:
   - An introduction explaining the topic
   - Key benefits (with specific claims)
   - Key risks (with specific claims)
   - Current scientific consensus
   - Practical recommendations
4. Make it about 500-800 words
5. Include specific claims that can be fact-checked (some should have citations, some might be questionable)

Write the research now. Use the filesystem tool to create {RESEARCH_FILE}."""

        result = await session.execute(prompt)
        print(f"{Color.GREEN}Initial draft created{Color.ENDC}")
        # Show snippet of result
        if len(result) > 300:
            print(f"{Color.CYAN}{result[:300]}...{Color.ENDC}")
        else:
            print(f"{Color.CYAN}{result}{Color.ENDC}")


async def observer_review(
    observer_name: str,
    observer_role: str,
    observer_instructions: str,
    loader: ModuleLoader,
    round_num: int,
) -> int:
    """An observer reviews the research and creates issues for problems found."""
    print(f"\n{Color.MAGENTA}  [{observer_name}] Reviewing (Round {round_num})...{Color.ENDC}")

    config = load_mount_plan("observer")
    # Update actor for this specific observer
    config = json.loads(json.dumps(config))  # Deep copy
    for tool in config.get("tools", []):
        if tool.get("module") == "tool-issue":
            tool["config"]["actor"] = observer_name.lower().replace(" ", "-")

    async with AmplifierSession(config, loader=loader) as session:
        prompt = f"""You are the **{observer_name}**, a specialized reviewer.

**Your Role:** {observer_role}

**Your Focus:** {observer_instructions}

**Task for Round {round_num}:**
1. Read the research file at: {RESEARCH_FILE}
2. Analyze it from your specialized perspective
3. If you find issues in your domain, create issues using the issue tool:
   - Type: "task"
   - Priority: 2
   - Title: Brief description of the problem
   - Description: Detailed explanation of what's wrong and suggestion for improvement
   - Metadata: {{"observer": "{observer_name}", "round": {round_num}}}
4. Only create NEW issues - don't repeat issues you've already raised
5. Create at most 2 issues per review round (focus on the most important)
6. If the content is good from your perspective, say "No issues found"

First read the file, then provide your review."""

        result = await session.execute(prompt)

        # Count issues created (rough heuristic based on response)
        issues_created = result.lower().count("created") + result.lower().count("issue")
        issues_created = min(issues_created, 2)  # Cap at 2

        if "no issues" in result.lower() or "no problems" in result.lower():
            print(f"{Color.GREEN}  [{observer_name}] No issues found{Color.ENDC}")
            return 0
        else:
            # Show snippet
            snippet = result[:200] + "..." if len(result) > 200 else result
            print(f"{Color.YELLOW}  [{observer_name}] {snippet}{Color.ENDC}")
            return issues_created


async def researcher_address_feedback(loader: ModuleLoader, round_num: int) -> bool:
    """Researcher checks for and addresses feedback issues."""
    print(f"\n{Color.BLUE}{Color.BOLD}=== RESEARCHER: Addressing Feedback (Round {round_num}) ==={Color.ENDC}")

    config = load_mount_plan("researcher")

    async with AmplifierSession(config, loader=loader) as session:
        prompt = f"""You are the research compiler. Check for feedback from the observers.

**Task:**
1. Use the issue tool to list all open issues (status=open)
2. For each issue:
   - Read the feedback carefully
   - Update the research file ({RESEARCH_FILE}) to address the concern
   - Close the issue with a note about what you changed
3. If there are no open issues, respond with "No feedback to address"

Focus on quality improvements based on the feedback. Update the file and close the issues."""

        result = await session.execute(prompt)

        if "no feedback" in result.lower() or "no open issues" in result.lower() or "no issues" in result.lower():
            print(f"{Color.GREEN}No feedback to address{Color.ENDC}")
            return False
        else:
            print(f"{Color.GREEN}Feedback addressed{Color.ENDC}")
            snippet = result[:300] + "..." if len(result) > 300 else result
            print(f"{Color.CYAN}{snippet}{Color.ENDC}")
            return True


async def run_observer_round(loader: ModuleLoader, round_num: int) -> int:
    """Run all observers in parallel for a review round."""
    print(f"\n{Color.MAGENTA}{Color.BOLD}=== OBSERVERS: Review Round {round_num} ==={Color.ENDC}")

    observers = [
        (
            "Skeptic",
            "Question unsupported or dubious claims",
            "Look for claims that lack citations, seem exaggerated, or contradict common knowledge. "
            "Flag statements that need better evidence or qualification.",
        ),
        (
            "Depth Seeker",
            "Identify areas needing more detail",
            "Look for topics mentioned briefly that deserve more exploration, missing important aspects, "
            "or areas where the reader might want more practical information.",
        ),
        (
            "Clarity Editor",
            "Flag confusing or unclear passages",
            "Look for jargon that isn't explained, sentences that are hard to follow, "
            "logical jumps that might confuse readers, or structure that could be improved.",
        ),
    ]

    # Run observers in parallel
    tasks = [
        asyncio.create_task(observer_review(name, role, instructions, loader, round_num))
        for name, role, instructions in observers
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_issues = 0
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"{Color.RED}  [{observers[i][0]}] Error: {result}{Color.ENDC}")
        elif isinstance(result, int):
            total_issues += result

    return total_issues


async def main():
    """Main orchestration."""
    print(
        f"""
{Color.BOLD}======================================================================{Color.ENDC}
{Color.BOLD}  Research Compiler with Fact-Checkers Demo{Color.ENDC}
{Color.BOLD}  Observer Pattern: Bottom-Up Feedback{Color.ENDC}
{Color.BOLD}======================================================================{Color.ENDC}
    """
    )

    # Validate API key
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        print(f"{Color.RED}ERROR: Valid ANTHROPIC_API_KEY not set{Color.ENDC}\n")
        print("Please set your API key:")
        print("  export ANTHROPIC_API_KEY='sk-ant-api03-...'")
        return

    print(f"{Color.GREEN}API key validated{Color.ENDC}\n")

    # Clean workspace
    workspace = Path.cwd() / ".demo-workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(exist_ok=True)

    work_dir = Path.cwd() / "work"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(exist_ok=True)

    print(f"Workspace: {workspace}")
    print(f"Output: {work_dir}")
    print(f"Research topic: {RESEARCH_TOPIC}")

    # Set up module loading
    try:
        search_paths = get_module_search_paths()

        for search_path in search_paths:
            for module_dir in search_path.iterdir():
                if module_dir.is_dir() and module_dir.name.startswith("amplifier-module-"):
                    path_str = str(module_dir)
                    if path_str not in sys.path:
                        sys.path.insert(0, path_str)

        loader = ModuleLoader(search_paths=search_paths)
        print(f"{Color.GREEN}Module loader initialized{Color.ENDC}\n")

    except Exception as e:
        print(f"{Color.RED}Failed to initialize module loader: {e}{Color.ENDC}")
        return

    print("=" * 70)

    # Phase 1: Initial research draft
    await researcher_initial_draft(loader, workspace)

    # Phase 2-N: Observer feedback loop
    for round_num in range(1, MAX_ROUNDS + 1):
        print(f"\n{'=' * 70}")
        print(f"{Color.BOLD}FEEDBACK ROUND {round_num} of {MAX_ROUNDS}{Color.ENDC}")
        print("=" * 70)

        # Let observers review
        await asyncio.sleep(2)  # Brief pause for readability
        issues_created = await run_observer_round(loader, round_num)

        if issues_created == 0:
            print(f"\n{Color.GREEN}{Color.BOLD}All observers satisfied! No more issues.{Color.ENDC}")
            break

        # Researcher addresses feedback
        await asyncio.sleep(2)
        had_feedback = await researcher_address_feedback(loader, round_num)

        if not had_feedback:
            print(f"\n{Color.GREEN}{Color.BOLD}No feedback to address. Research complete!{Color.ENDC}")
            break

    else:
        print(f"\n{Color.YELLOW}Maximum rounds ({MAX_ROUNDS}) reached.{Color.ENDC}")

    # Final summary
    print(
        f"""
{'=' * 70}
{Color.GREEN}{Color.BOLD}Demo Complete!{Color.ENDC}
{'=' * 70}

{Color.CYAN}Research file: {work_dir / 'research.md'}{Color.ENDC}

{Color.BOLD}Pattern Demonstrated:{Color.ENDC}
- Researcher works autonomously on content
- Observers watch and provide specialized feedback
- Issues flow bottom-up (observers create, researcher addresses)
- Natural convergence when observers are satisfied

{Color.BOLD}Key Differences from Foreman-Worker:{Color.ENDC}
- No central coordinator/delegator
- Main session IS the worker (researcher)
- Feedback emerges from observation, not assignment
- Quality improves through autonomous critique

{Color.BOLD}Observer Types Used:{Color.ENDC}
- Skeptic: Questioned unsupported claims
- Depth Seeker: Identified areas needing expansion
- Clarity Editor: Flagged confusing passages
    """
    )


if __name__ == "__main__":
    asyncio.run(main())
