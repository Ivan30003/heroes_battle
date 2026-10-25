"""Слоты героев: preview (подготовка) и battle (бой)."""
from __future__ import annotations

import pygame

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
    """Слот боя: портрет + имя + HP + мана + рамка активного."""

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
        self.portrait: pygame.Surface | None = None

    def update_from_view(self, hero_view) -> None:
        self.hero_id = hero_view.hero_id
        self.hero_name = hero_view.name
        self.team = hero_view.team
        self.hp = hero_view.hp
        self.hp_max = max(hero_view.hp_max, 1)
        self.mana = hero_view.mana
        self.mana_max = max(hero_view.mana_max, 1)
        self.alive = hero_view.alive

        if hero_view.hero_id:
            idx = None
            # найдём sprite_path из game_data через name — но проще через id
            # (передаётся в конструкторе BattleScreen; здесь только если сменился)
            if self._portrait_hero_id != hero_view.hero_id:
                self.portrait = self._load_portrait(hero_view.hero_id)
                self._portrait_hero_id = hero_view.hero_id
        else:
            self.portrait = None
            self._portrait_hero_id = ""

    _portrait_hero_id: str = ""

    def _load_portrait(self, hero_id: str):
        tpl = getattr(self, "_hero_templates", {}).get(hero_id)
        if tpl is None:
            return None
        return self.assets.hero_portrait(tpl["sprite_path"])

    def set_hero_templates(self, templates_by_id: dict) -> None:
        self._hero_templates = templates_by_id

    def draw(self, surface: pygame.Surface) -> None:
        bg = COLORS["team_top"] if self.team == 0 else COLORS["team_bottom"]
        draw_beveled_rect(surface, bg, self.rect, self.bevel)

        if self.portrait:
            surface.blit(self.portrait, self.rect.topleft)

        # Плашка с именем сверху
        if self.hero_name:
            font = self.theme.font(14, bold=True)
            txt = font.render(self.hero_name, True, COLORS["text"])
            badge = pygame.Surface((txt.get_width() + 8, 20), pygame.SRCALPHA)
            badge.fill((0, 0, 0, 190))
            badge.blit(txt, (4, 2))
            surface.blit(badge, (self.rect.x, self.rect.y))

        # Мана (тонкая полоса)
        mana_y = self.rect.bottom - 22
        pygame.draw.rect(surface, COLORS["mana_bg"],
                         (self.rect.x + 4, mana_y, self.rect.w - 8, 6))
        mf = self.mana / self.mana_max if self.mana_max > 0 else 0
        if mf > 0:
            pygame.draw.rect(surface, COLORS["mana"],
                             (self.rect.x + 4, mana_y,
                              int((self.rect.w - 8) * mf), 6))

        # HP (полоса над маной)
        hp_y = self.rect.bottom - 14
        pygame.draw.rect(surface, COLORS["hp_bg"],
                         (self.rect.x + 4, hp_y, self.rect.w - 8, 8))
        hf = self.hp / self.hp_max if self.hp_max > 0 else 0
        if hf > 0:
            pygame.draw.rect(surface, COLORS["hp"],
                             (self.rect.x + 4, hp_y,
                              int((self.rect.w - 8) * hf), 8))

        # Оверлей смерти
        if self.hero_id and not self.alive:
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, self.rect.topleft)

        # Подсветка активного героя
        if self.is_active and self.alive:
            pygame.draw.polygon(surface, COLORS["accent"],
                                octagon_points(self.rect, self.bevel), 3)
        else:
            pygame.draw.polygon(surface, COLORS["panel"],
                                octagon_points(self.rect, self.bevel), 2)