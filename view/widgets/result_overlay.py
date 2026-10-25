"""Оверлей результата боя."""
from __future__ import annotations

import pygame

from view.theme import COLORS
from view.widgets.button import Button
from view.widgets.draw_utils import draw_beveled_rect


class ResultOverlay:
    def __init__(self, app, winner_team, on_restart, on_menu):
        self.app = app
        self.theme = app.theme
        self.winner_team = winner_team

        pw, ph = 700, 380
        px = (app.width - pw) // 2
        py = (app.height - ph) // 2
        self.panel_rect = pygame.Rect(px, py, pw, ph)

        bw, bh = 280, 70
        bx = px + (pw - bw) // 2
        self.restart_button = Button(
            (bx, py + ph - bh * 2 - 60, bw, bh), "Ещё раз", on_restart,
            theme=self.theme, font_size=26,
        )
        self.menu_button = Button(
            (bx, py + ph - bh - 40, bw, bh), "В меню", on_menu,
            theme=self.theme, font_size=26,
        )

    def handle_event(self, event) -> None:
        self.restart_button.handle_event(event)
        self.menu_button.handle_event(event)

    def draw(self, surface) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surface.blit(overlay, (0, 0))

        draw_beveled_rect(surface, COLORS["panel"], self.panel_rect, 20)
        pygame.draw.rect(surface, COLORS["accent"], self.panel_rect, 3)

        if self.winner_team is None:
            text, color = "Ничья", COLORS["text"]
        elif self.winner_team == 0:
            text, color = "Победила верхняя команда!", COLORS["team_top"]
        else:
            text, color = "Победила нижняя команда!", COLORS["team_bottom"]

        title_font = self.theme.font(46, bold=True)
        title = title_font.render(text, True, COLORS["accent"])
        surface.blit(title, title.get_rect(
            center=(self.panel_rect.centerx, self.panel_rect.y + 90)))

        self.restart_button.draw(surface)
        self.menu_button.draw(surface)