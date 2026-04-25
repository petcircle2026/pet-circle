"""
OnboardingService â€” Orchestrator for the onboarding workflow.

Responsible for:
1. Coordinating state machine transitions
2. Validating user input using validators
3. Parsing GPT responses using parsers
4. Delegating to existing handlers in app.services.onboarding
5. Sending prompts via WhatsApp

This service bridges the new domain layer (state machine, validators, parsers)
with the existing monolithic onboarding.py.

Over time, this will absorb the core business logic from onboarding.py,
allowing that file to shrink to ~100 lines.
"""

import logging
from app.domain.onboarding.state_machine import OnboardingState, OnboardingStateMachine

logger = logging.getLogger(__name__)


class OnboardingService:
    """
    Orchestrates onboarding workflow.

    Thin wrapper over existing onboarding.py handlers. Will gradually absorb
    logic as we decompose the monolith.
    """

    def __init__(self, db):
        """
        Initialize service.

        Args:
            db: SQLAlchemy Session instance
        """
        self.db = db
        self.state_machine = OnboardingStateMachine()

    async def handle_message(
        self,
        user,
        text: str,
        send_fn,
        message_data: dict | None = None,
    ) -> None:
        """
        Process one onboarding message.

        Delegates to the existing onboarding.py handler until decomposition
        is complete.

        Args:
            user: User instance
            text: User's reply text
            send_fn: Async function to send WhatsApp messages
            message_data: Optional webhook message metadata
        """
        # Import here to avoid circular deps
        from app.services.whatsapp.onboarding import handle_onboarding_step

        try:
            await handle_onboarding_step(
                self.db,
                user,
                text,
                send_fn,
                message_data=message_data,
            )
        except Exception as e:
            logger.exception("Onboarding message handler failed: %s", str(e))
            raise

    def get_next_state(self, current_state: str | OnboardingState) -> OnboardingState | None:
        """Get the next state after current state."""
        return self.state_machine.get_next_state(current_state)

    def is_onboarding_complete(self, user) -> bool:
        """Check if user's onboarding is complete."""
        return user.onboarding_state == OnboardingState.COMPLETE.value

