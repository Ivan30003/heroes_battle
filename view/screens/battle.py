"""M3: заглушка боевого экрана.

Показывает 10 слотов с HP/маной и текущий ход. В M4 здесь появятся
панель действий, лог боя, подсветка валидных целей.
"""
from __future__ import annotations

import pygame

from view.theme import COLORS
from view.widgets.hero_slot import HeroSlotBattle


SLOT_W = 184
SLOT_H = 150
SLOT_GAP = 25
TEAM_SIZE = 5


def _slots_x_start(screen_w: int) -> int:
    total = TEAM_SIZE * SLOT_W + (TEAM_SIZE - 1) * SLOT_GAP
    return (screen_w - total) // 2


class BattleScreen:
    def __init__(self, app, controller):
        self.app = app
        self.controller = controller
        self.theme = app.theme

        w = app.width
        x_start = _slots_x_start(w)

        self.slot_rects = [
            (x_start + i * (SLOT_W + SLOT_GAP), 180, SLOT_W, SLOT_H)
            for i in range(5)
        ] + [
            (x_start + i * (SLOT_W + SLOT_GAP), 660, SLOT_W, SLOT_H)
            for i in range(5)
        ]

        templates = app.game_data["index"]["heroes"]
        self.slots = [HeroSlotBattle(r, self.theme, app.assets)
                      for r in self.slot_rects]
        for slot in self.slots:
            slot.set_hero_templates(templates)

        self.title_font = self.theme.font(32, bold=True)
        self.info_font = self.theme.font(22)
        self.hint_font = self.theme.font(20)

        self.snapshot = controller.snapshot()
        self._sync_slots()

    def _sync_slots(self) -> None:
        active = self.snapshot.active_slot
        for i, hv in enumerate(self.snapshot.heroes):
            self.slots[i].update_from_view(hv)
            self.slots[i].is_active = (i == active)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.return_to_menu()

    def update(self, dt: float) -> None:
        self.controller.update(dt)
        self.snapshot = self.controller.snapshot()
        self._sync_slots()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS["bg"])

        for slot in self.slots:
            slot.draw(surface)

        # заголовок с раундом
        title = self.title_font.render(
            f"Раунд {self.snapshot.round_number}", True, COLORS["accent"],
        )
        surface.blit(title, title.get_rect(center=(self.app.width // 2, 40)))

        # статус
        from control.battle_controller import ControllerState
        st = self.controller.state
        if st == ControllerState.BATTLE_END:
            w = self.snapshot.winner_team
            text = "Ничья" if w is None else (
                "Победила верхняя команда" if w == 0
                else "Победила нижняя команда"
            )
            color = COLORS["accent"]
        elif st == ControllerState.WAIT_FOR_ACTION:
            active = self.snapshot.active_slot
            text = f"Ход героя на слоте {active} — M4: панель действий появится в M4"
            color = COLORS["text_dim"]
        elif st == ControllerState.AI_THINKING:
            text = "AI думает…"
            color = COLORS["text_dim"]
        else:
            text = "…"
            color = COLORS["text_dim"]

        msg = self.info_font.render(text, True, color)
        surface.blit(msg, msg.get_rect(center=(self.app.width // 2, 460)))

        # подсказка
        hint = self.hint_font.render(
            "M4: полный боевой интерфейс. Esc — в меню.",
            True, COLORS["text_dim"],
        )
        surface.blit(hint, hint.get_rect(center=(self.app.width // 2,
                                                 self.app.height - 60)))