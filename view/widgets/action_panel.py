"""Панель действий активного героя: Атака / Способности / Медитация."""
from __future__ import annotations

import pygame

from control.public_api import ActionKind
from view.theme import COLORS
from view.widgets.button import Button
from view.widgets.tooltip import draw_tooltip


class ActionPanel:
    BTN_W = 160
    BTN_H = 70
    BTN_GAP = 6

    def __init__(self, rect, theme, battle, controller):
        self.rect = pygame.Rect(rect)
        self.theme = theme
        self.battle = battle
        self.controller = controller
        self.buttons: list[tuple[Button, dict]] = []
        self._build()

    def _build(self) -> None:
        self.buttons.clear()
        actor_slot = self.battle.current_actor()
        if actor_slot is None:
            return
        actor = self.battle.hero_at(actor_slot)
        available = set(self.battle.available_actions(actor_slot))
        available_abilities = set(self.battle.available_abilities(actor_slot))

        n = 1 + len(actor.template.ability_ids) + 1
        total_w = n * self.BTN_W + (n - 1) * self.BTN_GAP
        x = self.rect.x + (self.rect.w - total_w) // 2
        y = self.rect.y

        # Атака
        b = Button((x, y, self.BTN_W, self.BTN_H), "Атака", None,
                   self.theme, enabled=ActionKind.ATTACK in available,
                   font_size=22, bevel=6)
        b.on_click = lambda: self.controller.on_action_button(ActionKind.ATTACK)
        self.buttons.append((b, {"type": "attack"}))
        x += self.BTN_W + self.BTN_GAP

        # Способности
        for aid in actor.template.ability_ids:
            ab = self.battle.abilities[aid]
            b = Button((x, y, self.BTN_W, self.BTN_H), ab.name, None,
                       self.theme, enabled=aid in available_abilities,
                       font_size=18, bevel=6)
            b.on_click = (lambda ability_id=aid:
                          self.controller.on_action_button(ActionKind.ABILITY,
                                                           ability_id))
            self.buttons.append((b, {"type": "ability", "ability": ab}))
            x += self.BTN_W + self.BTN_GAP

        # Медитация
        b = Button((x, y, self.BTN_W, self.BTN_H), "Медитация", None,
                   self.theme, enabled=ActionKind.MEDITATE in available,
                   font_size=22, bevel=6)
        b.on_click = lambda: self.controller.on_action_button(ActionKind.MEDITATE)
        self.buttons.append((b, {"type": "meditate"}))

    def rebuild(self) -> None:
        self._build()

    def handle_event(self, event) -> None:
        for btn, _ in self.buttons:
            btn.handle_event(event)

    def draw(self, surface) -> None:
        for btn, _ in self.buttons:
            btn.draw(surface)

        mouse_pos = pygame.mouse.get_pos()
        font = self.theme.font(16)
        for btn, meta in self.buttons:
            if btn.hovered and btn.enabled and meta["type"] == "ability":
                ab = meta["ability"]
                lines = [
                    ab.name,
                    f"Стоимость: {ab.mana_cost} маны",
                    ab.description,
                ]
                draw_tooltip(surface, font, lines,
                             (mouse_pos[0] + 15, mouse_pos[1] + 15))
                break