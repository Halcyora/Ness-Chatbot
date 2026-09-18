"""
Local LLM provider stub for future on-premises deployment.

This provider will call a local LLM service (Ollama, vLLM, etc.)
running on company infrastructure instead of using paid APIs.

Not yet implemented - will be completed in a later phase.
"""

from typing import Optional, List, Dict, Any
from .base_provider import LLMProvider


class LocalProvider(LLMProvider):
    """
    Local LLM provider for on-premises deployment.

    Configuration via environment variables:
    - LOCAL_LLM_ENDPOINT: Base URL of local LLM service (e.g., http://localhost:8000)
    - LOCAL_GENERATION_MODEL: Model name for text generation
    - LOCAL_EMBEDDINGS_MODEL: Model name for embeddings

    TODO: Implement HTTP calls to local LLM service when company infrastructure is ready.
    """

    def __init__(self):
        """Initialize local LLM provider."""
        raise NotImplementedError(
            "LocalProvider is not yet implemented.\n"
            "This provider is designed for future on-premises deployment.\n"
            "Set LLM_PROVIDER=bedrock to use AWS Bedrock instead."
        )

    def generate(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Generate text using local LLM service."""
        raise NotImplementedError(
            "LocalProvider.generate() not yet implemented. "
            "Use BedrockProvider (LLM_PROVIDER=bedrock) for now."
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local LLM service."""
        raise NotImplementedError(
            "LocalProvider.embed() not yet implemented. "
            "Use BedrockProvider (LLM_PROVIDER=bedrock) for now."
        )

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "local"
