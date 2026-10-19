"""LLM Client factory function."""
import os

from api.services.llm.client import LLMClient
from api.services.llm.fake_client import FakeLLMClient
from api.services.llm.oci_client import OCIGenAIClient


def get_llm_client() -> LLMClient:
    """Return configured LLMClient based on environment settings."""
    provider = os.getenv("LLM_PROVIDER", "fake").lower()
    if provider == "oci":
        return OCIGenAIClient()
    return FakeLLMClient()
