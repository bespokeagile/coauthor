"""Three-tier LLM detection utility.

Tier 1: No API key (pure local analysis)
Tier 2: API key available (CLI semantic features)
Tier 3: API key + UI (full semantic dashboard)
"""

import os


def has_llm_key() -> bool:
    """Check if any supported LLM API key is configured."""
    return bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )


def get_tier() -> int:
    """Return the current feature tier.

    1 = no key (local analysis only)
    2 = key available (CLI semantic features)
    3 = key + UI (detected client-side)
    """
    if not has_llm_key():
        return 1
    return 2  # UI detection happens client-side


def get_provider() -> str:
    """Return the name of the configured LLM provider, or empty string."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return ""
