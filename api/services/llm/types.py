"""Data types for LLM requests and responses."""
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    estimated_cost: Decimal = Decimal("0.0000")
    model_name: str = "fake-model"
    prompt_version: str = "1.0"
