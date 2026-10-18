"""M0: заглушка главного меню. Настоящее меню — в M3."""
from __future__ import annotations

import pygame

from view.theme import COLORS


class MenuScreen:
    def __init__(self, app):
        self.app = app
        theme = app.theme
        self.title_font = theme.font(96, bold=True)
        self.sub_font = theme.font(36)
        self.info_font = theme.font(26)
        self.hint_font = theme.font(22)

    def handle_event(self, event: pygame.event.Event) -> None:
        # В M0 кнопок нет; реагируем только на Esc (его ловит App.run)
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS["bg"])
        cx = surface.get_width() // 2

        title = self.title_font.render("Hero Battle", True, COLORS["accent"])
        surface.blit(title, title.get_rect(center=(cx, 260)))

        sub = self.sub_font.render("M0 · каркас проекта собран", True, COLORS["text"])
        surface.blit(sub, sub.get_rect(center=(cx, 380)))

        data = self.app.game_data
        stats = (
            f"Загружено: героев {len(data['heroes'])}, "
            f"способностей {len(data['abilities'])}, "
            f"эффектов {len(data['effects'])}, "
            f"пассивок {len(data['passives'])}"
        )
        info = self.info_font.render(stats, True, COLORS["text_dim"])
        surface.blit(info, info.get_rect(center=(cx, 480)))

        hint = self.hint_font.render(
            "Esc — выход.  Дальнейшие экраны появятся в M3–M4.",
            True, COLORS["text_dim"],
        )
        surface.blit(hint, hint.get_rect(center=(cx, surface.get_height() - 80)))