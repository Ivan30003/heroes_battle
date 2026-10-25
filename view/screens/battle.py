"""Полный боевой экран: слоты, панель действий, лог, оверлей результата."""
from __future__ import annotations

import pygame

from control.public_api import ControllerState, EventType
from view.theme import COLORS
from view.widgets.action_panel import ActionPanel
from view.widgets.battle_log import BattleLog
from view.widgets.button import Button
from view.widgets.hero_slot import HeroSlotBattle
from view.widgets.result_overlay import ResultOverlay


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
        self.battle = controller.battle

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

        panel_rect = (x_start, 380, SLOT_W * 5 + SLOT_GAP * 4, 90)
        self.action_panel = ActionPanel(panel_rect, self.theme,
                                        self.battle, self.controller)

        self.cancel_button = Button(
            (w - 280, 390, 220, 60), "Отмена", None, self.theme,
            font_size=24, bevel=6, enabled=False,
        )
        self.cancel_button.on_click = self._on_cancel_click

        self.menu_button = Button(
            (30, 30, 180, 55), "В меню", None, self.theme,
            font_size=22, bevel=6,
        )
        self.menu_button.on_click = self.app.return_to_menu

        self.battle_log = BattleLog((w - 380, 180, 360, 780), self.theme)

        self.title_font = self.theme.font(32, bold=True)
        self.status_font = self.theme.font(22)

        self.snapshot = controller.snapshot()
        self._sync_slots()
        self.battle_log.set_lines(self.controller.log_lines)
        self._last_log_len = len(self.controller.log)

        self.result_overlay: ResultOverlay | None = None
        self._last_state = None

    # ------------------------------------------------------------- helpers

    def _sync_slots(self) -> None:
        active = self.snapshot.active_slot
        for i, hv in enumerate(self.snapshot.heroes):
            self.slots[i].update_from_view(hv)
            self.slots[i].is_active = (i == active)
            self.slots[i].highlight_target = False

        if self.controller.state == ControllerState.WAIT_FOR_TARGET:
            for t in self.controller.valid_targets_for_current_action():
                if 0 <= t < len(self.slots):
                    self.slots[t].highlight_target = True

    def _on_cancel_click(self) -> None:
        self.controller.on_cancel()
        self.action_panel.rebuild()
        self.cancel_button.enabled = False
        self._sync_slots()

    def _on_slot_click(self, slot_idx: int) -> None:
        if self.controller.state != ControllerState.WAIT_FOR_TARGET:
            return
        if self.controller.on_target_click(slot_idx):
            self.action_panel.rebuild()
            self.cancel_button.enabled = False
            self._sync_slots()

    def _on_restart_click(self) -> None:
        self.app.start_battle()

    def _update_ui_for_state(self) -> None:
        st = self.controller.state
        if st != self._last_state:
            if st == ControllerState.WAIT_FOR_ACTION:
                self.action_panel.rebuild()
            self.cancel_button.enabled = (st == ControllerState.WAIT_FOR_TARGET)
            self._last_state = st

    def _trigger_flash_for_event(self, event) -> None:
        t = event.type
        p = event.payload
        if t == EventType.DAMAGE:
            color = COLORS["crit_number"] if p.get("crit") else COLORS["hp"]
            self.slots[p["target"]].set_flash(color, 350)
        elif t == EventType.HEAL:
            self.slots[p["target"]].set_flash(COLORS["heal_number"], 400)
        elif t == EventType.ATTACK:
            self.slots[p["attacker"]].set_flash(COLORS["accent"], 200)
            self.slots[p["target"]].set_flash(COLORS["accent"], 200)
        elif t == EventType.DEATH:
            self.slots[p["slot"]].set_flash(COLORS["hp_bg"], 600)
        elif t == EventType.EFFECT_APPLIED:
            self.slots[p["slot"]].set_flash(COLORS["dot"], 300)
        elif t == EventType.MANA_GAIN:
            self.slots[p["slot"]].set_flash(COLORS["mana"], 200)

    # -------------------------------------------------------------- events

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.return_to_menu()
            return
        if self.result_overlay:
            self.result_overlay.handle_event(event)
            return
        self.menu_button.handle_event(event)
        if self.controller.state == ControllerState.WAIT_FOR_ACTION:
            self.action_panel.handle_event(event)
        if self.controller.state == ControllerState.WAIT_FOR_TARGET:
            self.cancel_button.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, slot in enumerate(self.slots):
                    if slot.rect.collidepoint(event.pos):
                        self._on_slot_click(i)
                        return
        self.battle_log.handle_event(event)

    def update(self, dt: float) -> None:
        self.controller.update(dt)

        new_events = self.controller.log[self._last_log_len:]
        for ev in new_events:
            self._trigger_flash_for_event(ev)
        self._last_log_len = len(self.controller.log)

        self.battle_log.set_lines(self.controller.log_lines)
        self.snapshot = self.controller.snapshot()
        self._sync_slots()
        self._update_ui_for_state()

        if (self.controller.state == ControllerState.BATTLE_END
                and self.result_overlay is None):
            self.result_overlay = ResultOverlay(
                self.app, self.snapshot.winner_team,
                on_restart=self._on_restart_click,
                on_menu=self.app.return_to_menu,
            )

    def draw(self, surface) -> None:
        surface.fill(COLORS["bg"])
        for slot in self.slots:
            slot.draw(surface)

        title = self.title_font.render(
            f"Раунд {self.snapshot.round_number}", True, COLORS["accent"])
        surface.blit(title, title.get_rect(center=(self.app.width // 2, 50)))

        st = self.controller.state
        if st == ControllerState.WAIT_FOR_ACTION:
            self.action_panel.draw(surface)
        elif st == ControllerState.WAIT_FOR_TARGET:
            msg = self.status_font.render(
                "Выберите цель (или Отмена)", True, COLORS["accent"])
            surface.blit(msg, msg.get_rect(center=(self.app.width // 2, 440)))
            self.cancel_button.draw(surface)
        elif st == ControllerState.AI_THINKING:
            msg = self.status_font.render("AI думает…", True,
                                          COLORS["text_dim"])
            surface.blit(msg, msg.get_rect(center=(self.app.width // 2, 440)))

        self.menu_button.draw(surface)
        self.battle_log.draw(surface)

        if self.result_overlay:
            self.result_overlay.draw(surface)