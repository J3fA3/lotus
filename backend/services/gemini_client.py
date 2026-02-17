"""
Gemini Client Service — Lotus v2

Clean interface to Google's Gemini 2.0 Flash API with:
- Structured output generation (JSON matching Pydantic schemas)
- Raw text generation
- Cost tracking and usage monitoring
- Async-safe execution via thread pool

Usage:
    from services.gemini_client import get_gemini_client
    client = get_gemini_client()
    result = await client.generate("Summarize this task...")
"""

import os
import json
import asyncio
import logging
import concurrent.futures
from typing import Type, TypeVar, Optional, Dict, Any
from pydantic import BaseModel
import google.generativeai as genai
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

# Shared thread pool for Gemini SDK calls (sync SDK, async wrapper)
_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)


class UsageStats(BaseModel):
    """Track Gemini API usage for cost monitoring."""
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    last_reset: datetime = datetime.now()

    def log_request(self, input_tokens: int, output_tokens: int):
        self.total_requests += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        # Gemini 2.0 Flash pricing: $0.075/1M input, $0.30/1M output
        cost = (input_tokens / 1_000_000) * 0.075 + (output_tokens / 1_000_000) * 0.30
        self.total_cost_usd += cost
        logger.info(
            f"Gemini request: {input_tokens} in, {output_tokens} out, "
            f"cost: ${cost:.6f} (total: ${self.total_cost_usd:.4f})"
        )


class GeminiClient:
    """Client for Google Gemini 2.0 Flash API."""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_AI_API_KEY", "")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.usage_stats = UsageStats()

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
            logger.warning("Gemini API key not configured — AI features will be unavailable")
            self.available = False
            self.model = None

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        temperature: float = 0.1,
        timeout: int = 10,
    ) -> T:
        """Generate structured output matching a Pydantic schema.

        Args:
            prompt: Input prompt for the model
            schema: Pydantic BaseModel class to validate against
            temperature: Sampling temperature (0.0-1.0)
            timeout: Maximum seconds to wait

        Returns:
            Instance of the schema class

        Raises:
            Exception: If Gemini is unavailable or generation fails
        """
        if not self.available:
            raise Exception("Gemini not available — set GOOGLE_AI_API_KEY")

        enhanced_prompt = f"""{prompt}

IMPORTANT: Return ONLY valid JSON matching the requested schema. Do not include markdown formatting or explanations."""

        loop = asyncio.get_event_loop()

        async def _generate():
            return await loop.run_in_executor(
                _thread_pool,
                lambda: self.model.generate_content(
                    enhanced_prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=2048,
                    ),
                ),
            )

        response = await asyncio.wait_for(_generate(), timeout=timeout)

        result_json = response.text.strip()
        if result_json.startswith("```json"):
            result_json = result_json.split("```json")[1].split("```")[0].strip()
        elif result_json.startswith("```"):
            result_json = result_json.split("```")[1].split("```")[0].strip()

        result = schema.model_validate_json(result_json)

        # Track usage (rough estimate: 4 chars per token)
        input_tokens = len(prompt) // 4
        output_tokens = len(result_json) // 4
        self.usage_stats.log_request(input_tokens, output_tokens)

        return result

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """Generate raw text response.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response

        Raises:
            Exception: If Gemini is unavailable or generation fails
        """
        if not self.available:
            raise Exception("Gemini not available — set GOOGLE_AI_API_KEY")

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            _thread_pool,
            lambda: self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            ),
        )

        result_text = response.text.strip()

        # Track usage
        input_tokens = len(prompt) // 4
        output_tokens = len(result_text) // 4
        self.usage_stats.log_request(input_tokens, output_tokens)

        return result_text

    def get_usage_stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self.usage_stats.total_requests,
            "total_input_tokens": self.usage_stats.total_input_tokens,
            "total_output_tokens": self.usage_stats.total_output_tokens,
            "total_cost_usd": round(self.usage_stats.total_cost_usd, 4),
            "last_reset": self.usage_stats.last_reset.isoformat(),
            "model_name": self.model_name,
            "available": self.available,
        }

    def reset_usage_stats(self):
        self.usage_stats = UsageStats()


# Singleton
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
