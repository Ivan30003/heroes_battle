"""Кнопка со скошенными углами: normal / hover / pressed / disabled."""
from __future__ import annotations

from typing import Callable

import pygame

from view.theme import COLORS
from view.widgets.draw_utils import draw_beveled_rect


class Button:
    def __init__(
        self,
        rect: tuple[int, int, int, int],
        text: str,
        on_click: Callable[[], None] | None,
        theme,
        enabled: bool = True,
        font_size: int = 24,
        bevel: int = 6,
        bg_normal=None,
        bg_hover=None,
        bg_pressed=None,
        bg_disabled=None,
    ):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.theme = theme
        self.enabled = enabled
        self.font_size = font_size
        self.bevel = bevel

        self.bg_normal = bg_normal or COLORS["button"]
        self.bg_hover = bg_hover or COLORS["button_hover"]
        self.bg_pressed = bg_pressed or COLORS["button_pressed"]
        self.bg_disabled = bg_disabled or COLORS["button_disabled"]

        self.hovered = False
        self.pressed = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
            return self.hovered
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.pressed
            self.pressed = False
            if was_pressed and self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        if not self.enabled:
            color = self.bg_disabled
            txt_color = COLORS["text_dim"]
        elif self.pressed and self.hovered:
            color = self.bg_pressed
            txt_color = COLORS["text"]
        elif self.hovered:
            color = self.bg_hover
            txt_color = COLORS["text"]
        else:
            color = self.bg_normal
            txt_color = COLORS["text"]

        draw_beveled_rect(surface, color, self.rect, self.bevel)

        if self.text:
            font = self.theme.font(self.font_size, bold=True)
            txt = font.render(self.text, True, txt_color)
            surface.blit(txt, txt.get_rect(center=self.rect.center))