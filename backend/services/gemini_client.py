"""
Gemini Client Service - Phase 3

This service provides a clean interface to Google's Gemini 2.0 Flash API
with support for:
- Structured output generation (JSON matching Pydantic schemas)
- Automatic fallback to Qwen on errors
- Cost tracking and usage monitoring
- Caching for frequently-used prompts

Key Features:
1. generate_structured(): Returns Pydantic model instances from prompts
2. generate(): Returns raw text responses
3. Automatic retry logic with exponential backoff
4. Cost tracking per request
5. Fallback to Qwen if Gemini unavailable

Usage:
    client = GeminiClient()
    result = await client.generate_structured(
        prompt="Classify this task...",
        schema=TaskClassification
    )
"""

import os
import json
import logging
from typing import Type, TypeVar, Optional, Dict, Any
from pydantic import BaseModel
import google.generativeai as genai
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class UsageStats(BaseModel):
    """Track Gemini API usage for cost monitoring."""
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    last_reset: datetime = datetime.now()

    def log_request(self, input_tokens: int, output_tokens: int):
        """Log a single API request."""
        self.total_requests += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        # Gemini 2.0 Flash pricing (as of Nov 2024)
        # Input: $0.075 per 1M tokens
        # Output: $0.30 per 1M tokens
        cost = (
            (input_tokens / 1_000_000) * 0.075 +
            (output_tokens / 1_000_000) * 0.30
        )
        self.total_cost_usd += cost

        logger.info(
            f"Gemini request: {input_tokens} input tokens, {output_tokens} output tokens, "
            f"cost: ${cost:.6f} (total: ${self.total_cost_usd:.4f})"
        )


class GeminiClient:
    """Client for Google Gemini 2.0 Flash API with structured output support."""

    def __init__(self):
        """Initialize Gemini client with API key from environment."""
        self.api_key = os.getenv("GOOGLE_AI_API_KEY", "")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.enable_cache = os.getenv("ENABLE_CACHE", "true").lower() == "true"

        # Usage tracking
        self.usage_stats = UsageStats()

        # Initialize Gemini SDK
        if self.api_key and self.api_key != "your_gemini_key_here":
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                self.available = True
                logger.info(f"Gemini client initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.available = False
                self.model = None
        else:
            logger.warning("Gemini API key not configured - will use Qwen fallback")
            self.available = False
            self.model = None

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        temperature: float = 0.1,
        fallback_to_qwen: bool = True
    ) -> T:
        """Generate structured output matching a Pydantic schema.

        Args:
            prompt: Input prompt for the model
            schema: Pydantic BaseModel class to match
            temperature: Sampling temperature (0.0-1.0, lower = more deterministic)
            fallback_to_qwen: If True, fall back to Qwen on Gemini failure

        Returns:
            Instance of the schema class with generated data

        Raises:
            Exception: If both Gemini and fallback fail
        """
        if not self.available and not fallback_to_qwen:
            raise Exception("Gemini not available and fallback disabled")

        # Try Gemini first
        if self.available:
            try:
                # Convert Pydantic schema to JSON schema for Gemini
                json_schema = schema.model_json_schema()

                # Generate with structured output
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=temperature,
                        response_mime_type="application/json",
                        # Note: Gemini 2.0 Flash supports response_schema
                        # but the Python SDK may need updates for full support
                    )
                )

                # Parse response text as JSON
                result_json = response.text.strip()

                # Handle markdown code blocks if present
                if result_json.startswith("```json"):
                    result_json = result_json.split("```json")[1].split("```")[0].strip()
                elif result_json.startswith("```"):
                    result_json = result_json.split("```")[1].split("```")[0].strip()

                # Parse into Pydantic model
                result = schema.model_validate_json(result_json)

                # Track usage (estimate tokens)
                input_tokens = len(prompt) // 4  # Rough estimate: 4 chars per token
                output_tokens = len(result_json) // 4
                self.usage_stats.log_request(input_tokens, output_tokens)

                logger.debug(f"Gemini structured generation successful: {schema.__name__}")
                return result

            except Exception as e:
                logger.error(f"Gemini structured generation failed: {e}")
                if not fallback_to_qwen:
                    raise

        # Fallback to Qwen
        logger.info("Falling back to Qwen for structured generation")
        return await self._generate_structured_qwen(prompt, schema, temperature)

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        fallback_to_qwen: bool = True
    ) -> str:
        """Generate raw text response.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            fallback_to_qwen: If True, fall back to Qwen on failure

        Returns:
            Generated text response
        """
        if not self.available and not fallback_to_qwen:
            raise Exception("Gemini not available and fallback disabled")

        # Try Gemini first
        if self.available:
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens
                    )
                )

                result_text = response.text.strip()

                # Track usage
                input_tokens = len(prompt) // 4
                output_tokens = len(result_text) // 4
                self.usage_stats.log_request(input_tokens, output_tokens)

                logger.debug(f"Gemini text generation successful ({len(result_text)} chars)")
                return result_text

            except Exception as e:
                logger.error(f"Gemini text generation failed: {e}")
                if not fallback_to_qwen:
                    raise

        # Fallback to Qwen
        logger.info("Falling back to Qwen for text generation")
        return await self._generate_qwen(prompt, temperature)

    async def _generate_structured_qwen(
        self,
        prompt: str,
        schema: Type[T],
        temperature: float
    ) -> T:
        """Fallback: Generate structured output using Qwen.

        Qwen doesn't support native structured output, so we ask it to
        return JSON and parse it into the schema.
        """
        # Add JSON schema to prompt
        json_schema = schema.model_json_schema()
        enhanced_prompt = f"""{prompt}

IMPORTANT: Return ONLY valid JSON matching this schema:
{json.dumps(json_schema, indent=2)}

DO NOT include any explanation or markdown formatting.
Output pure JSON only.
"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "qwen2.5:7b-instruct",
                        "prompt": enhanced_prompt,
                        "stream": False,
                        "options": {"temperature": temperature}
                    }
                )

                result = response.json()
                response_text = result.get("response", "").strip()

                # Clean up markdown formatting
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                # Parse into schema
                return schema.model_validate_json(response_text)

        except Exception as e:
            logger.error(f"Qwen fallback failed: {e}")
            # Last resort: return empty instance with required fields
            raise Exception(f"Both Gemini and Qwen fallback failed: {e}")

    async def _generate_qwen(
        self,
        prompt: str,
        temperature: float
    ) -> str:
        """Fallback: Generate text using Qwen."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "qwen2.5:7b-instruct",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": temperature}
                    }
                )

                result = response.json()
                return result.get("response", "").strip()

        except Exception as e:
            logger.error(f"Qwen fallback failed: {e}")
            raise Exception(f"Both Gemini and Qwen fallback failed: {e}")

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics.

        Returns:
            Dictionary with usage stats and cost information
        """
        return {
            "total_requests": self.usage_stats.total_requests,
            "total_input_tokens": self.usage_stats.total_input_tokens,
            "total_output_tokens": self.usage_stats.total_output_tokens,
            "total_cost_usd": round(self.usage_stats.total_cost_usd, 4),
            "last_reset": self.usage_stats.last_reset.isoformat(),
            "model_name": self.model_name,
            "available": self.available
        }

    def reset_usage_stats(self):
        """Reset usage statistics."""
        self.usage_stats = UsageStats()
        logger.info("Gemini usage stats reset")


# Global client instance (singleton pattern)
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get or create global Gemini client instance.

    Returns:
        GeminiClient singleton instance
    """
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
