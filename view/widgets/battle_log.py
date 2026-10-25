"""Скроллируемый лог боя."""
from __future__ import annotations

import pygame

from view.theme import COLORS


class BattleLog:
    def __init__(self, rect, theme, line_height: int = 22,
                 padding: int = 10):
        self.rect = pygame.Rect(rect)
        self.theme = theme
        self.line_height = line_height
        self.padding = padding
        self.font = theme.font(16)
        self.lines: list[str] = []
        self.scroll_offset = 0

    def set_lines(self, lines: list[str]) -> None:
        prev = len(self.lines)
        self.lines = list(lines)
        if self.scroll_offset > 0:
            self.scroll_offset = max(0, self.scroll_offset + (len(self.lines) - prev))

    @property
    def _visible_height(self) -> int:
        return self.rect.h - self.padding * 2

    @property
    def _visible_lines(self) -> int:
        return max(1, self._visible_height // self.line_height)

    @property
    def _max_scroll(self) -> int:
        return max(0, len(self.lines) - self._visible_lines)

    def handle_event(self, event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect.collidepoint(mx, my):
                self.scroll_offset = max(
                    0, min(self._max_scroll,
                           self.scroll_offset + event.y * 3),
                )

    def draw(self, surface) -> None:
        bg = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        bg.fill((20, 20, 28, 200))
        surface.blit(bg, self.rect.topleft)
        pygame.draw.rect(surface, COLORS["panel"], self.rect, 2)

        visible_n = self._visible_lines
        start = max(0, len(self.lines) - visible_n - self.scroll_offset)
        end = start + visible_n

        y = self.rect.y + self.padding
        for line in self.lines[start:end]:
            txt = self.font.render(line, True, COLORS["text"])
            surface.blit(txt, (self.rect.x + self.padding, y))
            y += self.line_height

        if self._max_scroll > 0:
            bar_x = self.rect.right - 8
            bar_h = self._visible_height
            thumb_h = max(30, int(bar_h * visible_n / max(1, len(self.lines))))
            if self._max_scroll > 0:
                ratio = 1.0 - self.scroll_offset / self._max_scroll
                thumb_y = int((bar_h - thumb_h) * ratio) + self.rect.y + self.padding
            else:
                thumb_y = self.rect.y + self.padding
            pygame.draw.rect(surface, COLORS["text_dim"],
                             (bar_x, thumb_y, 4, thumb_h))