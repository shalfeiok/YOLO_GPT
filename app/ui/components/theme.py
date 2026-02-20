"""Compatibility re-export for theme tokens.

Some UI modules historically imported Tokens from `app.ui.components.theme`.
The canonical location is now `app.ui.theme`.
"""

from app.ui.theme import Tokens, TokenSet, apply_token_set, ThemeManager, THEME_DARK, THEME_LIGHT

__all__ = [
    "Tokens",
    "TokenSet",
    "apply_token_set",
    "ThemeManager",
    "THEME_DARK",
    "THEME_LIGHT",
]
