# Demo

## Working Demos

- **demo.py** - WORKS. Full foreman-worker orchestrator demo with 4 issues.
  - Uses ForemanWorkerOrchestrator module
  - 2 coding tasks (fix auth, implement session management), 2 research tasks
  - **Demonstrates pending_user_input workflow**: Worker discovers it needs schema info,
    marks task as `pending_user_input`, foreman asks user, user provides info, task completes
  - Race condition fixes in IssueManager prevent duplicate claims and accidental reopening
  - All 4 issues complete successfully

- **test_single_worker.py** - WORKS. Test if a single worker can claim and complete an issue.
- **test_minimal_orchestrator.py** - WORKS. Does a worker WITHOUT system instructions work in orchestrator context?

## Broken/Legacy Demos

- demo2.py - Custom SimpleForemanWorkerOrchestrator inline, NO system instructions
- test_isolated_demo.py - Diagnostic version, may have shutdown issues

## Issue Status Values

- `open` - Available for workers to claim
- `in_progress` - Worker is actively working on it
- `pending_user_input` - Worker needs info from user (foreman should ask!)
- `blocked` - Blocked by another task dependency
- `closed` - Completed

## Key Fixes Applied

The IssueManager now has race condition guards:
1. Reloads from disk before updates (prevents stale cache)
2. Prevents reopening closed issues
3. Prevents claiming already-assigned issues
4. Idempotent close operations

