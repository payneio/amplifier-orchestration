"""
Test: Does a worker WITHOUT system instructions work in orchestrator context?
"""

import asyncio
import json
import sys
from pathlib import Path

# Add modules to path
modules_dir = Path(__file__).parent / "modules"
for module_dir in modules_dir.iterdir():
    if module_dir.is_dir() and module_dir.name.startswith("amplifier-module-"):
        sys.path.insert(0, str(module_dir))

from amplifier_core import AmplifierSession, ModuleLoader


def load_mount_plan(name: str) -> dict:
    path = Path(__file__).parent / "mount_plans" / f"{name}.json"
    with open(path) as f:
        return json.load(f)


async def test():
    print("=" * 70)
    print("MINIMAL ORCHESTRATOR WORKER TEST")
    print("=" * 70)

    loader = ModuleLoader(search_paths=[modules_dir])
    workspace = Path.cwd() / ".demo-workspace"
    if workspace.exists():
        import shutil

        shutil.rmtree(workspace)
    workspace.mkdir(exist_ok=True)

    # Step 1: Foreman creates issue
    print("\nStep 1: Creating issue with foreman...")
    foreman_config = load_mount_plan("foreman")
    async with AmplifierSession(foreman_config, loader=loader) as session:
        foreman_session_id = getattr(session, 'session_id', 'unknown')
        print(f"   Foreman session_id: {foreman_session_id}")
        await session.execute(
            "Create ONE test issue: title='Test task', issue_type='task', priority=1, metadata={'category': 'coding'}"
        )
    print("✓ Issue created")

    # Step 2: Worker tries to claim it (NO system instructions, like test_single_worker)
    print("\nStep 2: Worker WITHOUT system instructions...")
    worker_config = load_mount_plan("coding-worker")

    async with AmplifierSession(worker_config, loader=loader) as session:
        worker_session_id = getattr(session, 'session_id', 'unknown')
        print(f"   Worker session_id: {worker_session_id}")
        # Just send the prompt directly, NO system instructions
        prompt = """You are test-worker, a coding specialist.

Task: Find and work on one issue

1. Use the issue tool to list ready issues (filter: status=open)
2. Look for issues where metadata.category == "coding"
3. If you find one:
   - Update it to status=in_progress, assignee='test-worker'
   - Analyze the task
   - Complete your work and close the issue with a brief result
4. If no issues available for you, respond with "No work available"

Process ONE issue then stop."""

        result = await session.execute(prompt)
        print(f"\nWorker response:\n{result}\n")

    # Check database
    issues_file = workspace / ".amplifier/issues/issues.jsonl"
    if issues_file.exists():
        lines = issues_file.read_text().strip().split("\n")
        issues = [json.loads(l) for l in lines if l.strip()]
        for issue in issues:
            print(f"Issue: {issue['title']}")
            print(f"  Status: {issue['status']}")
            print(f"  Assignee: {issue.get('assignee', 'None')}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test())
