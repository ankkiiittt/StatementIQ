"""OCI Generative AI LLM client implementation."""
import os
import time
from decimal import Decimal

try:
    import oci
    from oci.generative_ai_inference.models import (
        ChatDetails,
        GenericChatRequest,
        OnDemandServingMode,
        TextContent,
        UserMessage,
    )
    OCI_AVAILABLE = True
except ImportError:
    OCI_AVAILABLE = False

from api.config import settings
from api.services.llm.client import LLMClient
from api.services.llm.types import LLMResponse


class OCIGenAIClient(LLMClient):
    """OCI Generative AI implementation of LLMClient."""

    def __init__(
        self,
        config_file: str | None = None,
        profile: str | None = None,
        compartment_id: str | None = None,
        model_id: str | None = None,
    ):
        if not OCI_AVAILABLE:
            raise RuntimeError("OCI Python SDK is not installed.")

        self.config_file = os.path.expanduser(config_file or settings.oci_config_file)
        self.profile = profile or settings.oci_profile
        self.compartment_id = compartment_id or settings.oci_compartment_id
        self.model_id = model_id or settings.oci_model_id or "cohere.command-r-plus-08-2024"

        try:
            self.config = oci.config.from_file(self.config_file, self.profile)
            self.client = oci.generative_ai_inference.GenerativeAiInferenceClient(config=self.config)
        except Exception as exc:
            # Stored so error can be reported when generate() is called
            self.client = None
            self.init_error = str(exc)

    def generate(
        self,
        prompt: str,
        prompt_version: str = "1.0",
        temperature: float = 0.0,
    ) -> LLMResponse:
        if not self.client:
            raise RuntimeError(f"OCI Client is not configured: {getattr(self, 'init_error', 'unknown error')}")

        if not self.compartment_id:
            raise ValueError("OCI compartment_id is required.")

        start_time = time.perf_counter()

        chat_request = GenericChatRequest(
            messages=[
                UserMessage(
                    content=[TextContent(text=prompt)],
                )
            ],
            temperature=temperature,
            max_tokens=4000,
        )

        chat_details = ChatDetails(
            compartment_id=self.compartment_id,
            serving_mode=OnDemandServingMode(model_id=self.model_id),
            chat_request=chat_request,
        )

        # Retry with exponential backoff on transient errors
        max_retries = 3
        backoff_delay = 2.0
        response = None

        for attempt in range(max_retries):
            try:
                response = self.client.chat(chat_details)
                break
            except Exception as exc:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"OCI Generative AI request failed after {max_retries} attempts: {exc!s}") from exc
                time.sleep(backoff_delay)
                backoff_delay *= 2

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract message text and token metrics
        chat_response = response.data.chat_response
        text = ""
        if chat_response and chat_response.choices and chat_response.choices[0].message:
            text = chat_response.choices[0].message.content[0].text

        input_tokens = len(prompt) // 4
        output_tokens = len(text) // 4

        # Cost estimation: ~$3 per 1M input tokens, ~$15 per 1M output tokens for Command R+
        cost = (Decimal(input_tokens) * Decimal("0.000003")) + (Decimal(output_tokens) * Decimal("0.000015"))

        return LLMResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            estimated_cost=cost.quantize(Decimal("0.0001")),
            model_name=self.model_id,
            prompt_version=prompt_version,
        )
