# Worker Multi-Step Workflow Fix

## Problem

Workers were calling `issue_manager` to list issues but then STOPPING and responding to user instead of continuing to claim/work/close the issues. The loop-streaming orchestrator breaks out of its loop when no tool calls are present in the response.

## Root Cause

The system instructions and user prompt were not explicit enough about:
1. Completing the ENTIRE workflow in a single execution turn
2. Using multiple tool calls in sequence without stopping
3. Not responding with text until work is actually complete

## Solution Implemented

### File Modified
`modules/amplifier-module-orchestrator-foreman-worker/amplifier_orchestrator_foreman_worker/orchestrator.py`

### Change 1: Ultra-Explicit System Instructions (lines 202-239)

**Key additions:**
- "CRITICAL EXECUTION RULES" section emphasizing single-turn completion
- Explicit prohibition against stopping after listing issues
- Clear STEP-by-STEP workflow with exact tool call examples
- "EXECUTION RULES" reinforcing multi-tool usage
- "FORBIDDEN" section listing anti-patterns to avoid

**Key phrases added:**
- "You MUST complete the ENTIRE workflow in ONE execution cycle"
- "DO NOT stop after just listing issues - that's only step 1"
- "Continue calling tools until work is COMPLETE"
- "Execute ALL 5 steps in sequence during THIS turn"
- "Only respond with text AFTER completing work"

### Change 2: Ultra-Explicit User Prompt (lines 247-256)

**Before:**
```python
prompt = "Check for available work and process one issue if found."
```

**After:**
```python
prompt = (
    "Execute your complete workflow NOW in THIS turn:\n\n"
    "1. List all open issues\n"
    f"2. Find and claim ONE {worker_category} issue\n"
    "3. Complete the work described in that issue\n"
    "4. Close the completed issue\n\n"
    "Use multiple tool calls in sequence. "
    "Do NOT respond until work is complete or no work is found. "
    "Execute ALL steps now."
)
```

## Expected Behavior After Fix

### Before (Broken)
```
Worker → List issues → Receive 7 issues → Respond "Here are the open issues" → STOP
```

### After (Fixed)
```
Worker → List issues → Receive 7 issues → Claim issue 'abc123' →
Do work (use tools) → Close issue → Respond "Completed task abc123" → Loop continues
```

## Verification Steps

### 1. Check Logs for Multi-Tool Execution
```
INFO: Worker coding-worker-0: completed task
DEBUG: tool_use: issue_manager operation='list' status='open'
DEBUG: tool_use: issue_manager operation='update' issue_id='...' status='in_progress'
DEBUG: tool_use: write_file path='work/...'  # or other work tools
DEBUG: tool_use: issue_manager operation='close' issue_id='...'
```

### 2. Check Foreman Status Shows Progress
```
beads-task status

Expected output:
- Open: 0-2 issues (decreasing over time)
- In Progress: 1-2 issues (workers claiming work)
- Completed: 2-4 issues (workers finishing tasks)
```

### 3. Check Worker Responses
Workers should respond with:
- "Completed task [issue_id]" (when work done)
- "no work" (when no matching issues found)

NOT:
- "Here are the open issues..." (list without action)
- "I found these issues..." (analysis without execution)

## Testing Procedure

1. Run the foreman-worker demo:
   ```bash
   cd working/foreman-demo
   python run.py
   ```

2. Create tasks via foreman:
   ```
   > Create 3 coding tasks: task1, task2, task3
   ```

3. Monitor logs for worker behavior:
   ```bash
   tail -f amplifierd.log | grep -E "(Worker|tool_use|completed)"
   ```

4. Check status frequently:
   ```
   > status
   ```

5. Verify workers complete entire workflow:
   - List issues (tool call)
   - Claim issue (tool call)
   - Do work (tool calls)
   - Close issue (tool call)
   - Report completion (text response)

## Success Criteria

✅ Workers claim and complete issues in single execution turn
✅ Multiple tool calls executed in sequence
✅ Issues move from open → in_progress → completed
✅ Work artifacts created in work/ directory
✅ Workers report "completed task" not "found issues"
✅ No workers stopping after just listing issues

## Rollback Plan

If the fix doesn't work, revert to commit before this change:
```bash
git checkout HEAD~1 modules/amplifier-module-orchestrator-foreman-worker/amplifier_orchestrator_foreman_worker/orchestrator.py
```

## Next Steps If This Doesn't Work

If workers still stop early:
1. Add explicit "continue" token in system instructions
2. Modify loop-streaming orchestrator to require explicit "done" signal
3. Add tool call counting and force minimum threshold
4. Implement explicit multi-turn workflow tracking

## Notes

- This fix uses prompt engineering only - no orchestrator changes
- Relies on LLM following ultra-explicit instructions
- May need iteration if LLM still breaks out early
- Consider adding explicit "workflow state" tracking if needed
