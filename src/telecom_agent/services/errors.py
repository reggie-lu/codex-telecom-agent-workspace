class ConversationNotFoundError(Exception):
    """The conversation is missing or is not owned by the authenticated customer."""


class EscalationNotFoundError(Exception):
    """The escalation is missing or is not owned by the authenticated customer."""


class ActiveEscalationExistsError(Exception):
    """The conversation already has a non-terminal escalation."""
