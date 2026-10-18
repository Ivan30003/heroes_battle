"""Цвета, шрифты и константы UI. Единственное место для «косметики»."""
from __future__ import annotations

import os
from typing import Any

import pygame


COLORS = {
    "bg": (24, 24, 32),
    "panel": (44, 44, 56),
    "accent": (200, 160, 80),
    "text": (230, 230, 230),
    "text_dim": (150, 150, 160),
    "hp": (200, 60, 60),
    "hp_bg": (70, 30, 30),
    "mana": (80, 140, 240),
    "mana_bg": (30, 50, 100),
    "team_top": (60, 60, 90),
    "team_bottom": (90, 60, 60),
    "buff": (80, 200, 120),
    "debuff": (220, 80, 80),
    "dot": (170, 80, 220),
    "control": (230, 210, 60),
    "crit_number": (255, 220, 80),
    "heal_number": (120, 230, 120),
    "miss_number": (170, 170, 170),
    "button": (70, 90, 130),
    "button_hover": (90, 120, 170),
    "button_pressed": (50, 70, 100),
    "button_disabled": (60, 60, 70),
}


class Theme:
    def __init__(self, settings: dict[str, Any]):
        self.settings = settings
        self.fonts_dir = settings["paths"]["fonts"]
        self._font_cache: dict[tuple[int, bool], pygame.font.Font] = {}

    def font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._font_cache:
            path = self._find_font(bold)
            f = pygame.font.Font(path, size) if path else pygame.font.SysFont(None, size, bold=bold)
            self._font_cache[key] = f
        return self._font_cache[key]

    def _find_font(self, bold: bool) -> str | None:
        if not os.path.isdir(self.fonts_dir):
            return None
        suffix = "bold" if bold else "regular"
        for name in sorted(os.listdir(self.fonts_dir)):
            if name.lower().endswith(".ttf") and suffix in name.lower():
                return os.path.join(self.fonts_dir, name)
        return None