"""Главное меню."""
from __future__ import annotations

import pygame

from view.theme import COLORS
from view.widgets.button import Button


class MenuScreen:
    def __init__(self, app):
        self.app = app
        theme = app.theme
        self.title_font = theme.font(96, bold=True)
        self.sub_font = theme.font(28)
        self.hint_font = theme.font(20)

        w = app.width
        bw, bh = 400, 90
        bx = (w - bw) // 2

        self.start_button = Button(
            (bx, 500, bw, bh),
            "Начать подготовку",
            on_click=self._on_start,
            theme=theme, font_size=30,
        )
        self.quit_button = Button(
            (bx, 620, bw, bh),
            "Выход",
            on_click=self._on_quit,
            theme=theme, font_size=30,
        )

    def _on_start(self) -> None:
        self.app.start_preparation()

    def _on_quit(self) -> None:
        self.app.quit()

    def handle_event(self, event: pygame.event.Event) -> None:
        self.start_button.handle_event(event)
        self.quit_button.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS["bg"])
        cx = surface.get_width() // 2

        title = self.title_font.render("Hero Battle", True, COLORS["accent"])
        surface.blit(title, title.get_rect(center=(cx, 260)))

        sub = self.sub_font.render("Геройская битва", True, COLORS["text"])
        surface.blit(sub, sub.get_rect(center=(cx, 360)))

        self.start_button.draw(surface)
        self.quit_button.draw(surface)

        hint = self.hint_font.render(
            "Esc — выход", True, COLORS["text_dim"],
        )
        surface.blit(hint, hint.get_rect(center=(cx, surface.get_height() - 40)))