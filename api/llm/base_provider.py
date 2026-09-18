"""
Abstract base class for LLM providers.

Defines the interface that all LLM provider implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM implementations (OpenAI, Bedrock, Local, etc.) must inherit
    from this class and implement the required methods.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate text based on a prompt.

        Args:
            prompt: The input prompt/message
            tools: Optional list of tool definitions for tool-calling
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (list of floats)
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider (e.g., 'bedrock', 'openai')."""
        pass
