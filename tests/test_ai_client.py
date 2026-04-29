"""Tests del cliente unificado de IA."""
import pytest
from unittest.mock import MagicMock, patch

from app.core.ai_client import (
    AIConfig, build_ai_client, GeminiClient, GroqClient, OpenRouterClient,
    APIAuthenticationError, APIRateLimitError, handle_api_errors,
)


def test_build_ai_client_gemini():
    config = AIConfig(provider="gemini", api_key="test_key", model="gemini-1.5-flash")
    client = build_ai_client(config)
    assert isinstance(client, GeminiClient)
    assert client.get_provider_name() == "Google Gemini"


def test_build_ai_client_groq():
    config = AIConfig(provider="groq", api_key="test_key", model="llama-3.3-70b-versatile")
    client = build_ai_client(config)
    assert isinstance(client, GroqClient)
    assert client.get_provider_name() == "Groq"


def test_build_ai_client_openrouter():
    config = AIConfig(provider="openrouter", api_key="test_key", model="openai/gpt-4o-mini")
    client = build_ai_client(config)
    assert isinstance(client, OpenRouterClient)
    assert client.get_provider_name() == "OpenRouter"


def test_build_ai_client_invalid_provider():
    config = AIConfig(provider="unknown", api_key="x", model="y")
    with pytest.raises(ValueError):
        build_ai_client(config)


def test_handle_api_errors_authentication():
    @handle_api_errors
    def raise_auth():
        raise Exception("401 unauthorized invalid api key")

    with pytest.raises(APIAuthenticationError):
        raise_auth()


def test_handle_api_errors_rate_limit():
    @handle_api_errors
    def raise_rate():
        raise Exception("429 rate limit exceeded")

    with pytest.raises(APIRateLimitError):
        raise_rate()


def test_groq_generate_text():
    config = AIConfig(provider="groq", api_key="fake", model="llama-3.3-70b-versatile")
    client = GroqClient(api_key="fake", model="llama-3.3-70b-versatile")

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Respuesta de prueba"

    with patch("groq.Groq") as MockGroq:
        MockGroq.return_value.chat.completions.create.return_value = mock_response
        result = client.generate_text("system", "user")
        assert result == "Respuesta de prueba"
