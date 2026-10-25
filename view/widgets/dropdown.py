"""Выпадающий список. Поддерживает открытие вниз и вверх."""
from __future__ import annotations

from typing import Callable

import pygame

from view.theme import COLORS
from view.widgets.draw_utils import draw_beveled_rect


class Dropdown:
    def __init__(
        self,
        rect: tuple[int, int, int, int],
        options: list[str],
        current_index: int,
        on_change: Callable[[str, int], None] | None,
        theme,
        font_size: int = 22,
        bevel: int = 6,
        open_direction: str = "down",   # "down" | "up"
    ):
        self.rect = pygame.Rect(rect)
        self.options = list(options)
        self.current_index = current_index
        self.on_change = on_change
        self.theme = theme
        self.font_size = font_size
        self.bevel = bevel
        self.open_direction = open_direction

        self.open = False
        self.hovered = False
        self.hovered_option = -1

    def _option_rect(self, i: int) -> pygame.Rect:
        if self.open_direction == "down":
            y = self.rect.y + self.rect.h * (i + 1)
        else:
            y = self.rect.y - self.rect.h * (i + 1)
        return pygame.Rect(self.rect.x, y, self.rect.w, self.rect.h)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
            if self.open:
                self.hovered_option = -1
                for i in range(len(self.options)):
                    if self._option_rect(i).collidepoint(event.pos):
                        self.hovered_option = i
                        break
            return self.hovered or self.open

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.open = not self.open
                return True
            if self.open:
                for i in range(len(self.options)):
                    if self._option_rect(i).collidepoint(event.pos):
                        self.current_index = i
                        self.open = False
                        if self.on_change:
                            self.on_change(self.options[i], i)
                        return True
                self.open = False
        return False

    def draw(self, surface: pygame.Surface) -> None:
        bg = COLORS["button_hover"] if self.hovered else COLORS["button"]
        draw_beveled_rect(surface, bg, self.rect, self.bevel)
        self._draw_text(surface, self.options[self.current_index], self.rect)
        self._draw_chevron(surface)

        if self.open:
            for i, opt in enumerate(self.options):
                r = self._option_rect(i)
                opt_bg = COLORS["button_hover"] if i == self.hovered_option \
                    else COLORS["panel"]
                draw_beveled_rect(surface, opt_bg, r, self.bevel)
            for i, opt in enumerate(self.options):
                self._draw_text(surface, opt, self._option_rect(i))

    def _draw_text(self, surface, text, rect):
        font = self.theme.font(self.font_size, bold=False)
        txt = font.render(text, True, COLORS["text"])
        surface.blit(txt, txt.get_rect(center=rect.center))

    def _draw_chevron(self, surface):
        cx = self.rect.right - 22
        cy = self.rect.centery
        pygame.draw.polygon(surface, COLORS["text"],
                            [(cx - 8, cy - 4), (cx + 8, cy - 4), (cx, cy + 5)])