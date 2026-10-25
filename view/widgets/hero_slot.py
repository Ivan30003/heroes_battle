"""Слоты героев: preview (подготовка) и battle (бой)."""
from __future__ import annotations

import pygame
import math

from view.theme import COLORS
from view.widgets.draw_utils import draw_beveled_rect, octagon_points


class HeroSlotPreview:
    """Слот подготовки: портрет + имя. Без HP/маны."""

    def __init__(self, rect, theme, assets, bevel: int = 8, is_top: bool = True):
        self.rect = pygame.Rect(rect)
        self.theme = theme
        self.assets = assets
        self.bevel = bevel
        self.is_top = is_top

        self.hero_id: str | None = None
        self.hero_name: str = ""
        self.portrait: pygame.Surface | None = None

    def set_hero(self, hero_id: str, hero_name: str, sprite_path: str) -> None:
        self.hero_id = hero_id
        self.hero_name = hero_name
        self.portrait = self.assets.hero_portrait(sprite_path)

    def clear(self) -> None:
        self.hero_id = None
        self.hero_name = ""
        self.portrait = None

    def draw(self, surface: pygame.Surface) -> None:
        bg = COLORS["team_top"] if self.is_top else COLORS["team_bottom"]
        draw_beveled_rect(surface, bg, self.rect, self.bevel)

        if self.portrait:
            surface.blit(self.portrait, self.rect.topleft)

        if self.hero_name:
            font = self.theme.font(18, bold=True)
            txt = font.render(self.hero_name, True, COLORS["text"])
            badge = pygame.Surface(
                (self.rect.w, txt.get_height() + 6), pygame.SRCALPHA,
            )
            badge.fill((0, 0, 0, 170))
            badge.blit(txt, txt.get_rect(center=(badge.get_width() // 2,
                                                 badge.get_height() // 2)))
            surface.blit(badge, (self.rect.x, self.rect.bottom - badge.get_height()))

        pygame.draw.polygon(surface, COLORS["panel"],
                            octagon_points(self.rect, self.bevel), 2)


class HeroSlotBattle:
    """Слот боя: портрет, имя, HP, мана, подсветка активного/цели, flash."""

    FLASH_MAX_DURATION = 600  # мс, для расчёта fade-out

    def __init__(self, rect, theme, assets, bevel: int = 8):
        self.rect = pygame.Rect(rect)
        self.theme = theme
        self.assets = assets
        self.bevel = bevel

        self.hero_id: str = ""
        self.hero_name: str = ""
        self.team: int = 0
        self.hp: int = 0
        self.hp_max: int = 1
        self.mana: int = 0
        self.mana_max: int = 10
        self.alive: bool = False

        self.is_active: bool = False
        self.highlight_target: bool = False
        self.portrait: pygame.Surface | None = None

        self._portrait_hero_id: str = ""
        self._hero_templates: dict = {}
        self._flash_color: tuple[int, int, int] | None = None
        self._flash_until: int = 0

    def set_hero_templates(self, templates_by_id: dict) -> None:
        self._hero_templates = templates_by_id

    def update_from_view(self, hero_view) -> None:
        self.hero_id = hero_view.hero_id
        self.hero_name = hero_view.name
        self.team = hero_view.team
        self.hp = hero_view.hp
        self.hp_max = max(hero_view.hp_max, 1)
        self.mana = hero_view.mana
        self.mana_max = max(hero_view.mana_max, 1)
        self.alive = hero_view.alive

        if self._portrait_hero_id != hero_view.hero_id:
            if not hero_view.hero_id:
                self.portrait = None
            else:
                tpl = self._hero_templates.get(hero_view.hero_id)
                self.portrait = (self.assets.hero_portrait(tpl["sprite_path"])
                                 if tpl else None)
            self._portrait_hero_id = hero_view.hero_id

    def set_flash(self, color: tuple[int, int, int], duration_ms: int) -> None:
        self._flash_color = color
        self._flash_until = pygame.time.get_ticks() + duration_ms

    def draw(self, surface: pygame.Surface) -> None:
        bg = COLORS["team_top"] if self.team == 0 else COLORS["team_bottom"]
        draw_beveled_rect(surface, bg, self.rect, self.bevel)

        if self.portrait:
            surface.blit(self.portrait, self.rect.topleft)

        if self.hero_name:
            font = self.theme.font(14, bold=True)
            txt = font.render(self.hero_name, True, COLORS["text"])
            badge = pygame.Surface((txt.get_width() + 8, 20), pygame.SRCALPHA)
            badge.fill((0, 0, 0, 190))
            badge.blit(txt, (4, 2))
            surface.blit(badge, (self.rect.x, self.rect.y))

        mana_y = self.rect.bottom - 22
        pygame.draw.rect(surface, COLORS["mana_bg"],
                         (self.rect.x + 4, mana_y, self.rect.w - 8, 6))
        mf = self.mana / self.mana_max if self.mana_max > 0 else 0
        if mf > 0:
            pygame.draw.rect(surface, COLORS["mana"],
                             (self.rect.x + 4, mana_y,
                              int((self.rect.w - 8) * mf), 6))

        hp_y = self.rect.bottom - 14
        pygame.draw.rect(surface, COLORS["hp_bg"],
                         (self.rect.x + 4, hp_y, self.rect.w - 8, 8))
        hf = self.hp / self.hp_max if self.hp_max > 0 else 0
        if hf > 0:
            pygame.draw.rect(surface, COLORS["hp"],
                             (self.rect.x + 4, hp_y,
                              int((self.rect.w - 8) * hf), 8))

        if self.hero_id and not self.alive:
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, self.rect.topleft)

        # Flash
        now = pygame.time.get_ticks()
        if self._flash_color is not None:
            if now < self._flash_until:
                remaining = self._flash_until - now
                alpha = int(180 * remaining / self.FLASH_MAX_DURATION)
                alpha = max(0, min(180, alpha))
                overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
                overlay.fill((*self._flash_color, alpha))
                surface.blit(overlay, self.rect.topleft)
            else:
                self._flash_color = None

        # Подсветка валидной цели (пульсация)
        if self.highlight_target and self.alive:
            t = pygame.time.get_ticks() / 1000.0
            pulse = (math.sin(t * 6) + 1.0) / 2.0
            alpha = int(150 + 105 * pulse)
            surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.polygon(
                surf, (*COLORS["accent"], alpha),
                octagon_points(pygame.Rect(0, 0, *self.rect.size), self.bevel),
                3,
            )
            surface.blit(surf, self.rect.topleft)

        # Рамка активного
        if self.is_active and self.alive:
            pygame.draw.polygon(surface, COLORS["accent"],
                                octagon_points(self.rect, self.bevel), 3)
        else:
            pygame.draw.polygon(surface, COLORS["panel"],
                                octagon_points(self.rect, self.bevel), 2)