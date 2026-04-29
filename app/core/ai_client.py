"""Cliente unificado de IA con patrón Strategy. Un único punto de creación."""
import functools
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from app.utils.logger import get_logger

logger = get_logger()


class AIError(Exception):
    pass


class APIAuthenticationError(AIError):
    pass


class APIRateLimitError(AIError):
    pass


class APIConnectionError(AIError):
    pass


def handle_api_errors(func: Callable) -> Callable:
    """Decorador DRY que normaliza errores de todos los SDKs de IA."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIAuthenticationError:
            raise
        except APIRateLimitError:
            raise
        except AIError:
            raise
        except Exception as exc:
            exc_str = str(exc).lower()
            if any(k in exc_str for k in ("authentication", "api key", "invalid key", "unauthorized", "401")):
                raise APIAuthenticationError(f"API key inválida o sin permisos: {exc}") from exc
            if any(k in exc_str for k in ("rate limit", "quota", "429", "too many")):
                raise APIRateLimitError(f"Límite de solicitudes alcanzado. Espere un momento: {exc}") from exc
            if any(k in exc_str for k in ("connection", "network", "timeout", "unreachable")):
                raise APIConnectionError(f"Error de conexión con la API: {exc}") from exc
            raise AIError(f"Error inesperado de la API: {exc}") from exc
    return wrapper


@dataclass
class AIConfig:
    provider: str
    api_key: str
    model: str


class AIClientProtocol(ABC):
    """Contrato que deben cumplir todos los proveedores de IA."""

    @abstractmethod
    def validate_key(self) -> bool:
        """Realiza un ping mínimo para validar que la API key es correcta."""

    @abstractmethod
    def generate_text(self, system_prompt: str, user_content: str) -> str:
        """Genera texto dado un system prompt y contenido del usuario."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Retorna el nombre legible del proveedor."""


class GeminiClient(AIClientProtocol):
    """Cliente para Google Gemini."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def get_provider_name(self) -> str:
        return "Google Gemini"

    @handle_api_errors
    def validate_key(self) -> bool:
        import google.generativeai as genai
        genai.configure(api_key=self._api_key)
        client = genai.GenerativeModel(self._model)
        response = client.generate_content("di hola")
        return bool(response.text)

    @handle_api_errors
    def generate_text(self, system_prompt: str, user_content: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=self._api_key)
        client = genai.GenerativeModel(
            self._model,
            system_instruction=system_prompt,
        )
        response = client.generate_content(user_content)
        return response.text.strip()


class GroqClient(AIClientProtocol):
    """Cliente para Groq."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def get_provider_name(self) -> str:
        return "Groq"

    @handle_api_errors
    def validate_key(self) -> bool:
        from groq import Groq
        client = Groq(api_key=self._api_key)
        resp = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": "hola"}],
            max_tokens=5,
        )
        return bool(resp.choices[0].message.content)

    @handle_api_errors
    def generate_text(self, system_prompt: str, user_content: str) -> str:
        from groq import Groq
        client = Groq(api_key=self._api_key)
        resp = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return resp.choices[0].message.content.strip()


class OpenRouterClient(AIClientProtocol):
    """Cliente para OpenRouter (compatible con API de OpenAI)."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def get_provider_name(self) -> str:
        return "OpenRouter"

    @handle_api_errors
    def validate_key(self) -> bool:
        from openai import OpenAI
        client = OpenAI(api_key=self._api_key, base_url=self.BASE_URL)
        resp = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": "hola"}],
            max_tokens=5,
        )
        return bool(resp.choices[0].message.content)

    @handle_api_errors
    def generate_text(self, system_prompt: str, user_content: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=self._api_key, base_url=self.BASE_URL)
        resp = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return resp.choices[0].message.content.strip()


def build_ai_client(config: AIConfig) -> AIClientProtocol:
    """Factory: retorna la implementación correcta según la configuración."""
    clients = {
        "gemini": GeminiClient,
        "groq": GroqClient,
        "openrouter": OpenRouterClient,
    }
    cls = clients.get(config.provider)
    if not cls:
        raise ValueError(f"Proveedor de IA desconocido: '{config.provider}'")
    return cls(api_key=config.api_key, model=config.model)
