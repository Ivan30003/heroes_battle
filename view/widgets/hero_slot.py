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
    FLASH_MAX_DURATION = 600
    EFFECT_ICON_SIZE = 26
    EFFECT_ICON_GAP = 2
    EFFECT_ICON_MAX = 5

    def __init__(self, rect, theme, assets, bevel: int = 8):
        self.rect = pygame.Rect(rect)
        self.theme = theme
        self.assets = assets
        self.bevel = bevel

        self.hero_id = ""
        self.hero_name = ""
        self.team = 0
        self.hp = 0
        self.hp_max = 1
        self.mana = 0
        self.mana_max = 10
        self.alive = False

        self.is_active = False
        self.highlight_target = False
        self.portrait = None

        self._portrait_hero_id = ""
        self._hero_templates = {}
        self._flash_color = None
        self._flash_until = 0

        self.effect_views = ()
        self._icon_hit_rects: list[tuple[pygame.Rect, object]] = []

    def set_hero_templates(self, templates_by_id):
        self._hero_templates = templates_by_id

    def update_from_view(self, hero_view):
        self.hero_id = hero_view.hero_id
        self.hero_name = hero_view.name
        self.team = hero_view.team
        self.hp = hero_view.hp
        self.hp_max = max(hero_view.hp_max, 1)
        self.mana = hero_view.mana
        self.mana_max = max(hero_view.mana_max, 1)
        self.alive = hero_view.alive
        self.effect_views = tuple(hero_view.effects)

        if self._portrait_hero_id != hero_view.hero_id:
            if not hero_view.hero_id:
                self.portrait = None
            else:
                tpl = self._hero_templates.get(hero_view.hero_id)
                self.portrait = (self.assets.hero_portrait(tpl["sprite_path"])
                                 if tpl else None)
            self._portrait_hero_id = hero_view.hero_id

    def set_flash(self, color, duration_ms):
        self._flash_color = color
        self._flash_until = pygame.time.get_ticks() + duration_ms

    def get_effect_at(self, pos):
        for icon_rect, ev in self._icon_hit_rects:
            if icon_rect.collidepoint(pos):
                return ev
        return None

    def draw(self, surface):
        self._icon_hit_rects = []

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

        self._draw_effect_icons(surface)
        self._draw_bars(surface)

        if self.hero_id and not self.alive:
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, self.rect.topleft)

        self._draw_flash(surface)
        self._draw_borders(surface)

    # ------------------------------------------------------------ internals

    def _draw_effect_icons(self, surface):
        if not self.effect_views or not self.alive:
            return
        size = self.EFFECT_ICON_SIZE
        gap = self.EFFECT_ICON_GAP
        x = self.rect.x + 4
        y = self.rect.bottom - 24 - size - 4

        shown = 0
        total = len(self.effect_views)
        for ev in self.effect_views:
            if shown >= self.EFFECT_ICON_MAX:
                break
            icon = self.assets.effect_icon(ev.family)
            icon = pygame.transform.smoothscale(icon, (size, size))
            icon_rect = pygame.Rect(x, y, size, size)

            backdrop = pygame.Surface((size, size), pygame.SRCALPHA)
            backdrop.fill((0, 0, 0, 120))
            surface.blit(backdrop, icon_rect.topleft)
            surface.blit(icon, icon_rect.topleft)

            if ev.stacks > 1:
                bf = self.theme.font(11, bold=True)
                badge = bf.render(f"×{ev.stacks}", True, COLORS["text"])
                brect = badge.get_rect(bottomright=(icon_rect.right - 1,
                                                   icon_rect.bottom - 1))
                pygame.draw.rect(surface, (0, 0, 0, 200),
                                 brect.inflate(4, 2))
                surface.blit(badge, brect)

            if ev.rounds_left <= 1:
                pygame.draw.rect(surface, COLORS["hp"],
                                 icon_rect, 2)

            self._icon_hit_rects.append((icon_rect, ev))
            x += size + gap
            shown += 1

        remaining = total - shown
        if remaining > 0:
            bf = self.theme.font(13, bold=True)
            badge = bf.render(f"+{remaining}", True, COLORS["text_dim"])
            surface.blit(badge, (x, y + 6))

    def _draw_bars(self, surface):
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

    def _draw_flash(self, surface):
        if self._flash_color is None:
            return
        now = pygame.time.get_ticks()
        if now >= self._flash_until:
            self._flash_color = None
            return
        remaining = self._flash_until - now
        alpha = int(160 * remaining / self.FLASH_MAX_DURATION)
        overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        overlay.fill((*self._flash_color, max(0, min(160, alpha))))
        surface.blit(overlay, self.rect.topleft)

    def _draw_borders(self, surface):
        if self.highlight_target and self.alive:
            t = pygame.time.get_ticks() / 1000.0
            pulse = (math.sin(t * 6) + 1.0) / 2.0
            alpha = int(150 + 105 * pulse)
            surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.polygon(
                surf, (*COLORS["accent"], alpha),
                octagon_points(pygame.Rect(0, 0, *self.rect.size), self.bevel),
                3)
            surface.blit(surf, self.rect.topleft)

        if self.is_active and self.alive:
            pygame.draw.polygon(surface, COLORS["accent"],
                                octagon_points(self.rect, self.bevel), 3)
        else:
            pygame.draw.polygon(surface, COLORS["panel"],
                                octagon_points(self.rect, self.bevel), 2)