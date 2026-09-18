"""
LLM provider factory and abstractions.

Provides a provider-agnostic interface for LLM operations (generate, embed).
Supports multiple backends via environment variable configuration.
"""

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_provider import LLMProvider


def get_llm_provider() -> "LLMProvider":
    """
    Factory function to get the configured LLM provider.

    Reads LLM_PROVIDER environment variable:
    - 'bedrock' (default): AWS Bedrock with Titan models
    - 'local': Local on-premises LLM service (not yet implemented)

    Returns:
        Instantiated LLM provider

    Raises:
        ValueError: If LLM_PROVIDER is set to an unknown provider
        RuntimeError: If provider initialization fails (e.g., missing credentials)
    """
    provider_name = os.getenv("LLM_PROVIDER", "bedrock").lower()

    if provider_name == "bedrock":
        from .bedrock_provider import BedrockProvider
        return BedrockProvider()
    elif provider_name == "local":
        from .local_provider import LocalProvider
        return LocalProvider()
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider_name}'. "
            f"Valid options: 'bedrock', 'local'"
        )


# Export for convenience
from .base_provider import LLMProvider

__all__ = [
    "LLMProvider",
    "get_llm_provider",
]
