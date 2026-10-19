"""Abstract LLM Client interface."""
import json
import re
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from api.services.llm.types import LLMResponse

T = TypeVar("T", bound=BaseModel)


def clean_json_text(text: str) -> str:
    """Strip markdown code fences and extraneous whitespace from LLM response."""
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    return cleaned


class LLMClient(ABC):
    """Abstract interface for all LLM providers (OCI GenAI, Fake client, etc.)."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        prompt_version: str = "1.0",
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Generate text from the LLM."""
        pass

    def generate_json(
        self,
        prompt: str,
        pydantic_schema: type[T],
        prompt_version: str = "1.0",
    ) -> tuple[T, LLMResponse]:
        """Generate and validate a structured JSON object against a Pydantic schema."""
        response = self.generate(
            prompt=prompt,
            prompt_version=prompt_version,
            temperature=0.0,
        )
        cleaned = clean_json_text(response.text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Model output is not valid JSON: {exc!s}\nOutput: {cleaned[:200]}") from exc

        try:
            validated = pydantic_schema.model_validate(data)
            return validated, response
        except Exception as exc:
            raise ValueError(f"Model JSON failed schema validation: {exc!s}") from exc
