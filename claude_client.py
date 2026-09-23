"""Shared Anthropic client for the Qwallity AI modules.

Lives in its own module so both RAG_AI and text_classifier can use one client
without importing each other.
"""
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

# Haiku 4.5 is the cheapest current Claude model ($1/$5 per 1M tokens) and fits
# both workloads here: short intent labels and short grounded answers.
CLAUDE_MODEL = "claude-opus-5"

_claude_client = None


def get_claude_client():
    """Build the Claude client on first use.

    Constructed lazily so a missing ANTHROPIC_API_KEY surfaces where it is used
    rather than taking down the whole app at import time.
    """
    global _claude_client
    if _claude_client is None:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file."
            )
        _claude_client = anthropic.Anthropic(api_key=api_key)
    return _claude_client
