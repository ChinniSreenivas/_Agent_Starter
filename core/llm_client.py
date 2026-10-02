"""
Resilient LLM Client wrapper for Google GenAI (Gemini) with structured output enforcement,
quota-exhaustion detection, fast failover, and high-fidelity fallback.
"""

import time
from typing import Callable, Optional, Type, TypeVar
from pydantic import BaseModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

from google import genai
from google.genai import types
from google.genai.errors import ClientError, APIError

from core.config import settings
from core.logger import get_logger

logger = get_logger("core.llm_client")

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Manages LLM API calls with structured schema outputs, quota handling, and fallbacks."""

    def __init__(self):
        self._client: Optional[genai.Client] = None
        self.quota_exhausted: bool = False
        if settings.is_gemini_configured:
            try:
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info("Initialized Google GenAI client successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize GenAI client: {e}. Will use fallback.")
        else:
            logger.info("GEMINI_API_KEY not configured. Running in high-fidelity mock mode.")

    @property
    def is_live(self) -> bool:
        return self._client is not None and settings.is_gemini_configured and not self.quota_exhausted

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        fallback_fn: Optional[Callable[[], T]] = None,
        model_name: Optional[str] = None,
    ) -> T:
        """
        Executes a structured generation request against Gemini.
        Validates output against `response_model`.
        Fast failover to `fallback_fn` if Gemini is unavailable, rate-limited, or errors out.
        """
        # If quota is already known to be exhausted, immediately use fallback (zero latency)
        if self.quota_exhausted or not self.is_live:
            if fallback_fn:
                reason = "Free Tier 20 RPD Quota Exhausted" if self.quota_exhausted else "No API Key"
                logger.info(f"[{reason}] Serving structured {response_model.__name__} via heuristic fallback.")
                return fallback_fn()
            raise RuntimeError(f"Gemini client unavailable and no fallback provided for {response_model.__name__}")

        model = model_name or settings.GEMINI_MODEL
        start_time = time.perf_counter()

        def _execute_api_call(target_model: str) -> T:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_model,
                temperature=0.2,
            )
            if system_instruction:
                config.system_instruction = system_instruction

            response = self._client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )

            if hasattr(response, "parsed") and response.parsed is not None:
                if isinstance(response.parsed, response_model):
                    return response.parsed
                return response_model.model_validate(response.parsed)

            if response.text:
                return response_model.model_validate_json(response.text)

            raise ValueError("Empty response received from Gemini API.")

        try:
            result = _execute_api_call(model)
            duration = time.perf_counter() - start_time
            logger.info(f"Generated {response_model.__name__} via Gemini ({model}) in {duration:.2f}s")
            return result
        except Exception as e:
            err_str = str(e)
            is_quota_error = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota exceeded" in err_str

            if is_quota_error:
                logger.warning(f"Gemini Free-Tier Quota Exceeded (429 RESOURCE_EXHAUSTED). Marking quota_exhausted=True and engaging fallback.")
                self.quota_exhausted = True
                if fallback_fn:
                    return fallback_fn()
                raise e

            logger.error(f"Gemini call failed with error: {e}. Checking fallback.")
            if fallback_fn:
                logger.warning(f"Invoking heuristic fallback for {response_model.__name__}")
                return fallback_fn()
            raise e


# Global shared instance
llm_client = LLMClient()
