"""
Stub implementations for demo purposes.

Provides minimal ApprovalSystem and DisplaySystem implementations
to eliminate warnings when running demos without these systems configured.
"""

import logging

logger = logging.getLogger(__name__)


class StubApprovalSystem:
    """
    Minimal approval system that auto-approves everything.

    In a real system, this would present approval requests to the user
    and wait for their decision. For demos, we just auto-approve.
    """

    async def request_approval(self, request: dict) -> bool:
        """Auto-approve all requests for demo purposes."""
        logger.debug(f"Auto-approving: {request.get('message', 'unknown request')}")
        return True


class StubDisplaySystem:
    """
    Minimal display system that logs hook messages.

    In a real system, this would render messages in a UI.
    For demos, we just log them.
    """

    async def display_message(self, message: dict) -> None:
        """Log display messages."""
        msg_type = message.get('type', 'unknown')
        content = message.get('content', '')
        logger.debug(f"Display [{msg_type}]: {content[:100]}")

    async def display_hook(self, hook_data: dict) -> None:
        """Log hook execution."""
        hook_name = hook_data.get('hook_name', 'unknown')
        logger.debug(f"Hook executed: {hook_name}")
