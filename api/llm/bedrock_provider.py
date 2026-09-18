"""
AWS Bedrock LLM provider implementation.

Uses Titan models by default (most cost-optimized for this use case).
"""

import json
import os
from typing import Optional, List, Dict, Any
import boto3
from botocore.exceptions import ClientError

from .base_provider import LLMProvider


class BedrockProvider(LLMProvider):
    """
    AWS Bedrock LLM provider using Titan models.

    Configuration via environment variables:
    - BEDROCK_MODEL_ID: Model ID for text generation (default: amazon.nova-micro-v1:0)
    - BEDROCK_EMBEDDINGS_MODEL_ID: Model ID for embeddings (default: amazon.titan-embed-text-v1)
    - AWS_REGION: AWS region (default: us-east-1)
    - AWS_ACCESS_KEY_ID: AWS access key (optional, uses default credentials if not set)
    - AWS_SECRET_ACCESS_KEY: AWS secret key (optional, uses default credentials if not set)
    """

    def __init__(self):
        """Initialize Bedrock client and model IDs from environment."""
        self.model_id = os.getenv(
            "BEDROCK_MODEL_ID",
            "amazon.nova-micro-v1:0"
        )
        self.embeddings_model_id = os.getenv(
            "BEDROCK_EMBEDDINGS_MODEL_ID",
            "amazon.titan-embed-text-v1"
        )
        self.region = os.getenv("AWS_REGION", "us-east-1")

        # Initialize Bedrock runtime client
        try:
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=self.region
            )
            # Test connection
            self._test_connection()
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Bedrock client: {e}\n"
                f"Make sure AWS credentials are configured and Bedrock is available in {self.region}"
            )

    def _test_connection(self) -> None:
        """Test that we can connect to Bedrock."""
        try:
            # Try a minimal invoke to verify credentials and connectivity
            self.client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": "test"}]}],
                inferenceConfig={"maxTokens": 10, "temperature": 0.0},
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "AccessDenied":
                raise RuntimeError(
                    f"Access denied to Bedrock model {self.model_id}. "
                    f"Check AWS credentials and IAM permissions."
                )
            raise

    def generate(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate text using AWS Bedrock (Converse API - works across model families).

        Note: Tool-calling support would require additional LLM setup.
        For now, tools parameter is accepted but not used (future enhancement).

        Args:
            prompt: The input prompt
            tools: Optional tools (not yet implemented for Bedrock)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            Generated text response
        """
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "topP": 0.9,
                },
            )
            return response["output"]["message"]["content"][0]["text"].strip()

        except ClientError as e:
            raise RuntimeError(f"Bedrock API error: {e}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using AWS Bedrock Titan Embeddings model.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []

        try:
            for text in texts:
                response = self.client.invoke_model(
                    modelId=self.embeddings_model_id,
                    body=json.dumps({"inputText": text}),
                    contentType="application/json",
                    accept="application/json"
                )

                response_body = json.loads(response["body"].read())
                # Titan embeddings returns: {"embedding": [...]}
                if "embedding" in response_body:
                    embeddings.append(response_body["embedding"])
                else:
                    raise ValueError(f"Unexpected response format: {response_body}")

            return embeddings

        except ClientError as e:
            raise RuntimeError(f"Bedrock embeddings API error: {e}")

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "bedrock"

    def __repr__(self) -> str:
        """String representation."""
        return f"BedrockProvider(model={self.model_id}, region={self.region})"
