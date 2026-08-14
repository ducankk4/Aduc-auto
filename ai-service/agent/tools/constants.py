"""Shared constants for agent tool definitions."""

# Metadata key marking a tool as sensitive: the subagent builder derives its
# interrupt_on (approval gate) map from this flag instead of hardcoding names.
REQUIRES_APPROVAL = "requires_approval"
