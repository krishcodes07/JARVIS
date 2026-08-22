"""
Setup Validation — live checks used by the onboarding wizard.

Every check talks to the real provider so the wizard can only write a
configuration that actually works. This is what stops the classic first-run
failure: a plausible-looking ``embedding_model`` that the chosen provider has no
endpoint for, silently disabling vector memory forever.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Generous enough for a cold provider, short enough not to stall onboarding.
_CHECK_TIMEOUT = 25.0


@dataclass(slots=True)
class CheckResult:
    """Outcome of a live provider check."""

    ok: bool
    message: str
    detail: dict[str, Any] | None = None

    def __bool__(self) -> bool:
        return self.ok


def _make_provider(provider_id: str) -> Any | None:
    """Build a protocol instance for *provider_id* from the catalog, or None."""
    from jarvis.providers.registry import ProviderRegistry

    registry = ProviderRegistry()
    registry.load()
    try:
        definition = registry.get(provider_id)
    except Exception as e:
        logger.debug("Provider '%s' not in catalog: %s", provider_id, e)
        return None

    import os

    from jarvis.core.constants import Protocol
    from jarvis.providers.models_dev import get_provider_env_vars

    raw_envs = get_provider_env_vars(
        provider_id, getattr(definition, "raw", None), filter_synonyms=False
    )
    api_key = ""
    for env_name in raw_envs:
        val = os.getenv(env_name, "").strip()
        if val:
            api_key = val
            break
    if not api_key and definition.api_key_env:
        api_key = os.getenv(definition.api_key_env, "").strip()

    if not api_key:
        return None

    kwargs = {
        "api_key": api_key,
        "base_url": definition.base_url,
        "extra_headers": definition.extra_headers,
    }
    if definition.protocol == Protocol.ANTHROPIC:
        from jarvis.providers.protocols.anthropic import AnthropicProvider

        return AnthropicProvider(**kwargs)
    if definition.protocol == Protocol.GOOGLE:
        from jarvis.providers.protocols.google import GoogleProvider

        return GoogleProvider(**kwargs)
    from jarvis.providers.protocols.openai import OpenAIProvider

    return OpenAIProvider(**kwargs)


async def check_api_key(provider_id: str) -> CheckResult:
    """Verify a provider's credentials with a free model-list request.

    Uses ``list_models`` rather than a generation call so validating costs no
    tokens.

    Args:
        provider_id: The models.dev provider id.

    Returns:
        A :class:`CheckResult`; ``detail["models"]`` holds the count on success.
    """
    import asyncio

    provider = _make_provider(provider_id)
    if provider is None:
        return CheckResult(False, "No API key is set for this provider.")

    try:
        models = await asyncio.wait_for(provider.list_models(), timeout=_CHECK_TIMEOUT)
    except TimeoutError:
        return CheckResult(False, f"Timed out after {_CHECK_TIMEOUT:.0f}s.")
    except Exception as e:
        return CheckResult(False, _short(e))
    finally:
        with contextlib.suppress(Exception):
            await provider.close()

    count = len(models or [])
    if not count:
        # Some gateways return an empty list without failing; the key may still
        # be fine, so this is reported but not treated as fatal by the caller.
        return CheckResult(True, "Reachable, but returned no model list.", {"models": 0})
    return CheckResult(True, f"Key valid — {count} models visible.", {"models": count})


async def check_embedding(provider_id: str, model: str) -> CheckResult:
    """Verify that *provider_id* can actually embed text with *model*.

    Args:
        provider_id: The models.dev provider id.
        model: The embedding model id to test.

    Returns:
        A :class:`CheckResult`; ``detail["dimension"]`` holds the vector size.
    """
    import asyncio

    if not model:
        return CheckResult(False, "No embedding model selected.")

    provider = _make_provider(provider_id)
    if provider is None:
        return CheckResult(False, "No API key is set for this provider.")

    try:
        vectors = await asyncio.wait_for(
            provider.embed(["JARVIS embedding check"], model), timeout=_CHECK_TIMEOUT
        )
    except NotImplementedError:
        return CheckResult(False, "This provider has no embeddings API.")
    except TimeoutError:
        return CheckResult(False, f"Timed out after {_CHECK_TIMEOUT:.0f}s.")
    except Exception as e:
        return CheckResult(False, _short(e))
    finally:
        with contextlib.suppress(Exception):
            await provider.close()

    if not vectors or not vectors[0]:
        return CheckResult(False, "Provider returned an empty embedding.")

    dim = len(vectors[0])
    return CheckResult(True, f"Embeddings working — {dim} dimensions.", {"dimension": dim})


async def check_local_embedding(
    on_progress: Any | None = None,
) -> CheckResult:
    """Download (if needed) and test the bundled offline embedding model.

    Args:
        on_progress: Optional ``(downloaded, total)`` callback for the download.

    Returns:
        A :class:`CheckResult`; ``detail["dimension"]`` holds the vector size.
    """
    from jarvis.memory.vector.local_embedder import LocalEmbedder, LocalEmbeddingError

    embedder = LocalEmbedder()
    try:
        await embedder.prepare(on_progress)
        vectors = await embedder.embed(["JARVIS embedding check"])
    except LocalEmbeddingError as e:
        return CheckResult(False, _short(e))
    except Exception as e:
        return CheckResult(False, _short(e))

    if not vectors or not vectors[0]:
        return CheckResult(False, "Local model returned an empty embedding.")

    dim = len(vectors[0])
    return CheckResult(
        True,
        f"Local model ready — {dim} dimensions, no API key needed.",
        {"dimension": dim, "model": embedder.model_name},
    )


async def check_extraction_model(provider_id: str, model: str) -> CheckResult:
    """Verify that *model* exists on *provider_id* with a 1-token generation.

    Long-term memory extraction fails silently when the configured model id
    belongs to a different provider, so this checks the exact pair that will be
    written to the config.

    Args:
        provider_id: The models.dev provider id.
        model: The chat model id used for extraction.

    Returns:
        A :class:`CheckResult`.
    """
    import asyncio

    from jarvis.providers.base import GenerationConfig, Message

    if not model:
        return CheckResult(False, "No model selected.")

    provider = _make_provider(provider_id)
    if provider is None:
        return CheckResult(False, "No API key is set for this provider.")

    try:
        await asyncio.wait_for(
            provider.generate(
                [Message(role="user", content="ok")],
                GenerationConfig(model=model, temperature=0.0, max_tokens=1),
            ),
            timeout=_CHECK_TIMEOUT,
        )
    except TimeoutError:
        return CheckResult(False, f"Timed out after {_CHECK_TIMEOUT:.0f}s.")
    except Exception as e:
        return CheckResult(False, _short(e))
    finally:
        with contextlib.suppress(Exception):
            await provider.close()

    return CheckResult(True, f"'{model}' responded successfully.")


def _short(error: object, limit: int = 180) -> str:
    """Condense an exception into a single readable line."""
    text = " ".join(str(error).split())
    if not text:
        text = type(error).__name__
    return text if len(text) <= limit else text[: limit - 1] + "…"
