"""Тултип: полупрозрачная плашка с переносимым текстом.

Автоматически удерживается в границах окна.
"""
from __future__ import annotations

import pygame

from view.theme import COLORS


def draw_tooltip(surface: pygame.Surface, font: pygame.font.Font,
                 lines: list[str], pos: tuple[int, int],
                 max_width: int = 340, padding: int = 10,
                 line_spacing: int = 4) -> None:
    if not lines:
        return

    # Переносим длинные строки по словам
    wrapped: list[str] = []
    for line in lines:
        if not line:
            wrapped.append("")
            continue
        current = ""
        for word in line.split(" "):
            test = (current + " " + word).strip()
            if font.size(test)[0] <= max_width - padding * 2:
                current = test
            else:
                if current:
                    wrapped.append(current)
                current = word
        if current:
            wrapped.append(current)

    widths = [font.size(s)[0] for s in wrapped] or [0]
    w = min(max(widths) + padding * 2, max_width)
    line_h = font.get_height() + line_spacing
    h = line_h * len(wrapped) + padding * 2 - line_spacing

    x, y = pos
    sw, sh = surface.get_size()
    if x + w > sw - 8:
        x = sw - w - 8
    if y + h > sh - 8:
        y = sh - h - 8
    x = max(x, 8)
    y = max(y, 8)

    bg = pygame.Surface((w, h), pygame.SRCALPHA)
    bg.fill((15, 15, 25, 240))
    surface.blit(bg, (x, y))
    pygame.draw.rect(surface, COLORS["accent"], (x, y, w, h), 1)

    for i, line in enumerate(wrapped):
        txt = font.render(line, True, COLORS["text"])
        surface.blit(txt, (x + padding, y + padding + i * line_h))