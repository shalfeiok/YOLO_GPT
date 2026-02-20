"""
Design tokens: colors, spacing, radius. TokenSet per theme; current set updated by ThemeManager.
"""
from __future__ import annotations

from typing import Any


class TokenSet:
    """Immutable-like set of design tokens. ThemeManager copies dark/light into current."""

    __slots__ = (
        "background_main", "surface", "surface_hover",
        "primary", "primary_hover",
        "text_primary", "text_secondary",
        "border",
        "success", "warning", "error",
        "space_xs", "space_sm", "space_md", "space_lg", "space_xl",
        "radius_sm", "radius_md", "radius_lg",
        "card_padding", "border_width",
    )

    def __init__(
        self,
        *,
        background_main: str = "#1a1b26",
        surface: str = "#252736",
        surface_hover: str = "#2d2e3d",
        primary: str = "#3b82f6",
        primary_hover: str = "#60a5fa",
        text_primary: str = "#e2e8f0",
        text_secondary: str = "#94a3b8",
        border: str = "#334155",
        success: str = "#22c55e",
        warning: str = "#eab308",
        error: str = "#ef4444",
        space_xs: int = 4,
        space_sm: int = 8,
        space_md: int = 12,
        space_lg: int = 16,
        space_xl: int = 24,
        radius_sm: int = 6,
        radius_md: int = 10,
        radius_lg: int = 14,
        card_padding: int = 20,
        border_width: int = 1,
    ) -> None:
        self.background_main = background_main
        self.surface = surface
        self.surface_hover = surface_hover
        self.primary = primary
        self.primary_hover = primary_hover
        self.text_primary = text_primary
        self.text_secondary = text_secondary
        self.border = border
        self.success = success
        self.warning = warning
        self.error = error
        self.space_xs = space_xs
        self.space_sm = space_sm
        self.space_md = space_md
        self.space_lg = space_lg
        self.space_xl = space_xl
        self.radius_sm = radius_sm
        self.radius_md = radius_md
        self.radius_lg = radius_lg
        self.card_padding = card_padding
        self.border_width = border_width

    def copy_into(self, target: TokenSet) -> None:
        """Copy this set's values into target (mutates target)."""
        for key in self.__slots__:
            setattr(target, key, getattr(self, key))


# Predefined palettes
DARK = TokenSet(
    background_main="#1a1b26",
    surface="#252736",
    surface_hover="#2d2e3d",
    primary="#3b82f6",
    primary_hover="#60a5fa",
    text_primary="#e2e8f0",
    text_secondary="#94a3b8",
    border="#334155",
    success="#22c55e",
    warning="#eab308",
    error="#ef4444",
    space_xs=4, space_sm=8, space_md=12, space_lg=16, space_xl=24,
    radius_sm=6, radius_md=10, radius_lg=14,
    card_padding=20, border_width=1,
)

LIGHT = TokenSet(
    background_main="#f1f5f9",
    surface="#ffffff",
    surface_hover="#e2e8f0",
    primary="#2563eb",
    primary_hover="#3b82f6",
    text_primary="#0f172a",
    text_secondary="#64748b",
    border="#cbd5e1",
    success="#16a34a",
    warning="#ca8a04",
    error="#dc2626",
    space_xs=4, space_sm=8, space_md=12, space_lg=16, space_xl=24,
    radius_sm=6, radius_md=10, radius_lg=14,
    card_padding=20, border_width=1,
)

# Current tokens: mutable, updated by ThemeManager. Components use Tokens.primary etc.
Tokens: TokenSet = TokenSet()
DARK.copy_into(Tokens)


def apply_token_set(source: TokenSet) -> None:
    """Set current Tokens from source. Called by ThemeManager."""
    source.copy_into(Tokens)
