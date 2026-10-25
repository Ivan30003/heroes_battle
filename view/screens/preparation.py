"""Экран подготовки: 5+5 слотов, выбор героев, режим игры, кнопка старта."""
from __future__ import annotations

import pygame

from view.theme import COLORS
from view.widgets.button import Button
from view.widgets.dropdown import Dropdown
from view.widgets.hero_slot import HeroSlotPreview


SLOT_W = 184
SLOT_H = 150
SLOT_GAP = 25
TEAM_SIZE = 5


def _slots_x_start(screen_w: int) -> int:
    total = TEAM_SIZE * SLOT_W + (TEAM_SIZE - 1) * SLOT_GAP
    return (screen_w - total) // 2


class PreparationScreen:
    def __init__(self, app):
        self.app = app
        self.theme = app.theme
        self.session = app.session
        self.roster = [h["id"] for h in app.game_data["heroes"]]
        self.templates = app.game_data["index"]["heroes"]

        # дефолтные составы
        if not self.session.top.hero_ids:
            self.session.top.hero_ids = [
                self.roster[i % len(self.roster)] for i in range(TEAM_SIZE)
            ]
            self.session.top.ai = False
        if not self.session.bottom.hero_ids:
            self.session.bottom.hero_ids = [
                self.roster[i % len(self.roster)] for i in range(TEAM_SIZE)
            ]
            self.session.bottom.ai = True

        # координаты
        w = app.width
        x_start = _slots_x_start(w)

        self.top_slot_rects = [
            (x_start + i * (SLOT_W + SLOT_GAP), 180, SLOT_W, SLOT_H)
            for i in range(TEAM_SIZE)
        ]
        self.bottom_slot_rects = [
            (x_start + i * (SLOT_W + SLOT_GAP), 660, SLOT_W, SLOT_H)
            for i in range(TEAM_SIZE)
        ]

        # слоты
        self.top_slots = [
            HeroSlotPreview(r, self.theme, app.assets, is_top=True)
            for r in self.top_slot_rects
        ]
        self.bottom_slots = [
            HeroSlotPreview(r, self.theme, app.assets, is_top=False)
            for r in self.bottom_slot_rects
        ]

        # стрелки
        arrow_w, arrow_h = 30, 32
        self.top_arrows = []
        self.bottom_arrows = []
        for r in self.top_slot_rects:
            sx = r[0]
            sy = r[1] + SLOT_H + 8
            self.top_arrows.append((
                Button((sx + 57, sy, arrow_w, arrow_h), "◄", None,
                       self.theme, font_size=20, bevel=5),
                Button((sx + 97, sy, arrow_w, arrow_h), "►", None,
                       self.theme, font_size=20, bevel=5),
            ))
        for r in self.bottom_slot_rects:
            sx = r[0]
            sy = r[1] + SLOT_H + 8
            self.bottom_arrows.append((
                Button((sx + 57, sy, arrow_w, arrow_h), "◄", None,
                       self.theme, font_size=20, bevel=5),
                Button((sx + 97, sy, arrow_w, arrow_h), "►", None,
                       self.theme, font_size=20, bevel=5),
            ))

        # привязка колбэков стрелок
        for i, (left, right) in enumerate(self.top_arrows):
            left.on_click = (lambda idx=i: self._cycle("top", idx, -1))
            right.on_click = (lambda idx=i: self._cycle("top", idx, +1))
        for i, (left, right) in enumerate(self.bottom_arrows):
            left.on_click = (lambda idx=i: self._cycle("bottom", idx, -1))
            right.on_click = (lambda idx=i: self._cycle("bottom", idx, +1))

        # выпадающие списки режима
        dd_w, dd_h = 260, 50
        dd_x = (w - dd_w) // 2
        self.top_mode_dd = Dropdown(
            (dd_x, 15, dd_w, dd_h),
            options=["Человек", "Компьютер"],
            current_index=0 if not self.session.top.ai else 1,
            on_change=lambda _opt, idx: setattr(self.session.top, "ai", idx == 1),
            theme=self.theme, font_size=22, open_direction="down",
        )
        self.bottom_mode_dd = Dropdown(
            (dd_x, 1010, dd_w, dd_h),
            options=["Человек", "Компьютер"],
            current_index=0 if not self.session.bottom.ai else 1,
            on_change=lambda _opt, idx: setattr(self.session.bottom, "ai", idx == 1),
            theme=self.theme, font_size=22, open_direction="up",
        )

        # кнопка старта
        bw, bh = 400, 100
        self.start_button = Button(
            ((w - bw) // 2, 490, bw, bh),
            "НАЧАТЬ БИТВУ",
            on_click=self._on_start,
            theme=self.theme, font_size=34,
        )

        self._refresh_slots()

    # ------------------------------------------------------------ helpers

    def _cycle(self, side: str, slot_idx: int, delta: int) -> None:
        team = self.session.top if side == "top" else self.session.bottom
        if not self.roster:
            return
        current = team.hero_ids[slot_idx]
        idx = self.roster.index(current) if current in self.roster else 0
        idx = (idx + delta) % len(self.roster)
        team.hero_ids[slot_idx] = self.roster[idx]
        self._refresh_slots()

    def _refresh_slots(self) -> None:
        for i in range(TEAM_SIZE):
            tid = self.session.top.hero_ids[i]
            tpl = self.templates[tid]
            self.top_slots[i].set_hero(tid, tpl["name"], tpl["sprite_path"])

            bid = self.session.bottom.hero_ids[i]
            btpl = self.templates[bid]
            self.bottom_slots[i].set_hero(bid, btpl["name"], btpl["sprite_path"])

    def _on_start(self) -> None:
        self.app.start_battle()

    # ------------------------------------------------------------- events

    def handle_event(self, event: pygame.event.Event) -> None:
        self.top_mode_dd.handle_event(event)
        self.bottom_mode_dd.handle_event(event)
        for left, right in self.top_arrows:
            left.handle_event(event)
            right.handle_event(event)
        for left, right in self.bottom_arrows:
            left.handle_event(event)
            right.handle_event(event)
        self.start_button.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS["bg"])

        # слоты и стрелки
        for slot in self.top_slots:
            slot.draw(surface)
        for slot in self.bottom_slots:
            slot.draw(surface)
        for left, right in self.top_arrows:
            left.draw(surface)
            right.draw(surface)
        for left, right in self.bottom_arrows:
            left.draw(surface)
            right.draw(surface)

        # дропдауны
        self.top_mode_dd.draw(surface)
        self.bottom_mode_dd.draw(surface)

        # кнопка
        self.start_button.draw(surface)

        # подписи команд
        font = self.theme.font(22, bold=True)
        top_label = font.render("Верхняя команда", True, COLORS["text_dim"])
        bottom_label = font.render("Нижняя команда", True, COLORS["text_dim"])
        surface.blit(top_label, top_label.get_rect(center=(self.app.width // 2,
                                                           self.top_mode_dd.rect.bottom + 6)))
        surface.blit(bottom_label,
                     bottom_label.get_rect(center=(self.app.width // 2,
                                                   self.bottom_mode_dd.rect.top - 6)))