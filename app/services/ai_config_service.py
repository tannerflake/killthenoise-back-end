from __future__ import annotations

import os
from typing import Optional


class AIConfigService:
    """Configuration service for AI-related settings and API keys."""

    @staticmethod
    def get_claude_api_key() -> Optional[str]:
        """Get Claude API key from environment variables."""
        return os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    @staticmethod
    def is_ai_enabled() -> bool:
        """Check if AI features are enabled."""
        return AIConfigService.get_claude_api_key() is not None

    @staticmethod
    def get_ai_model() -> str:
        """Get the Claude model to use for analysis."""
        return os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")

    @staticmethod
    def get_max_tokens() -> int:
        """Get maximum tokens for AI responses."""
        try:
            return int(os.getenv("CLAUDE_MAX_TOKENS", "150"))
        except ValueError:
            return 150

    @staticmethod
    def get_ai_timeout() -> int:
        """Get timeout for AI requests in seconds."""
        try:
            return int(os.getenv("AI_TIMEOUT", "30"))
        except ValueError:
            return 30


def get_claude_api_key() -> Optional[str]:
    """Convenience function to get Claude API key."""
    return AIConfigService.get_claude_api_key()


def is_ai_enabled() -> bool:
    """Convenience function to check if AI is enabled."""
    return AIConfigService.is_ai_enabled()