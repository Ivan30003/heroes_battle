"""Загрузчик ассетов с умными плейсхолдерами.

- Если PNG существует — грузим и масштабируем.
- Иначе генерируем детерминированный плейсхолдер (цвет + метка),
  чтобы играть было можно без ассетов и визуально различать элементы.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any

import pygame


FAMILY_COLORS: dict[str, tuple[int, int, int]] = {
    "burn":          (230, 110,  40),
    "poison":        (100, 200,  80),
    "stun":          (250, 210,  50),
    "silence":       (150, 100, 210),
    "madness":       (220,  60, 220),
    "counter":       ( 80, 200, 220),
    "attack_down":   (160,  50,  50),
    "attack_up":     (240, 120,  80),
    "defense_down":  ( 90,  90, 160),
    "defense_up":    (100, 150, 240),
    "accuracy_down": (140, 140, 140),
    "heal_pct":      (100, 220, 120),
    "cleanse":       (220, 220, 100),
    "direct_damage": (200,  60,  60),
    "damage_over_time": (170, 80, 220),
}


def _stable_color(seed: str) -> tuple[int, int, int]:
    h = hashlib.md5(seed.encode("utf-8")).digest()
    # Держим цвета насыщенными и не слишком тёмными
    r = 80 + h[0] % 150
    g = 80 + h[1] % 150
    b = 80 + h[2] % 150
    return (r, g, b)


class AssetManager:
    def __init__(self, settings: dict[str, Any]):
        self.settings = settings
        self._images: dict[tuple, pygame.Surface] = {}

    # --------------------------------------------------------- low level

    def load_image(self, path: str,
                   size: tuple[int, int] | None = None) -> pygame.Surface:
        key = (path, size)
        if key in self._images:
            return self._images[key]
        if path and os.path.isfile(path):
            img = pygame.image.load(path).convert_alpha()
            if size is not None and img.get_size() != size:
                img = pygame.transform.smoothscale(img, size)
        else:
            img = self._generic_placeholder(size or (32, 32),
                                            os.path.basename(path or "?"))
        self._images[key] = img
        return img

    @staticmethod
    def _generic_placeholder(size, label: str) -> pygame.Surface:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((80, 60, 90, 220))
        pygame.draw.rect(surf, (200, 120, 220), surf.get_rect(), 2)
        return surf

    @staticmethod
    def _icon_with_letter(size: tuple[int, int], color,
                          letter: str) -> pygame.Surface:
        w, h = size
        surf = pygame.Surface(size, pygame.SRCALPHA)
        cx, cy = w // 2, h // 2
        pygame.draw.circle(surf, color, (cx, cy), min(w, h) // 2 - 1)
        pygame.draw.circle(surf, (20, 20, 30), (cx, cy), min(w, h) // 2 - 1, 2)
        font = pygame.font.SysFont(None, max(10, h - 6), bold=True)
        txt = font.render((letter or "?")[:1].upper(), True, (255, 255, 255))
        surf.blit(txt, txt.get_rect(center=(cx, cy)))
        return surf

    @staticmethod
    def _hero_placeholder(size: tuple[int, int],
                          seed: str) -> pygame.Surface:
        w, h = size
        surf = pygame.Surface(size)
        base = _stable_color(seed)
        # Двухцветный градиент
        for y in range(h):
            t = y / max(1, h - 1)
            color = (
                int(base[0] * (1 - t) + 30 * t),
                int(base[1] * (1 - t) + 30 * t),
                int(base[2] * (1 - t) + 40 * t),
            )
            pygame.draw.line(surf, color, (0, y), (w, y))
        pygame.draw.rect(surf, (20, 20, 30), (0, 0, w, h), 3)
        # Инициалы
        initials = "".join(p[:1].upper() for p in seed.split("_")[:2]) or "?"
        font = pygame.font.SysFont(None, 56, bold=True)
        txt = font.render(initials, True, (240, 240, 240))
        txt_bg = pygame.Surface((txt.get_width() + 20,
                                 txt.get_height() + 10), pygame.SRCALPHA)
        txt_bg.fill((0, 0, 0, 140))
        txt_bg.blit(txt, txt.get_rect(center=(txt_bg.get_width() // 2,
                                              txt_bg.get_height() // 2)))
        surf.blit(txt_bg, txt_bg.get_rect(center=(w // 2, h // 2)))
        return surf

    # ---------------------------------------------------------- semantic

    def hero_portrait(self, sprite_rel_path: str) -> pygame.Surface:
        ui = self.settings["ui"]
        size = (ui["slot_width"], ui["slot_height"])
        full = os.path.join(self.settings["paths"]["sprites"],
                            os.path.basename(sprite_rel_path))
        key = (full, size)
        if key in self._images:
            return self._images[key]
        if os.path.isfile(full):
            img = self.load_image(full, size)
        else:
            seed = os.path.splitext(os.path.basename(sprite_rel_path))[0] or "hero"
            img = self._hero_placeholder(size, seed)
            self._images[key] = img
        return img

    def effect_icon(self, family: str) -> pygame.Surface:
        size = self.settings["ui"]["effect_icon_size"]
        path = os.path.join(self.settings["paths"]["effect_icons"],
                            f"{family}.png")
        key = (path, (size, size))
        if key in self._images:
            return self._images[key]
        if os.path.isfile(path):
            img = self.load_image(path, (size, size))
        else:
            color = FAMILY_COLORS.get(family, _stable_color(family))
            img = self._icon_with_letter((size, size), color, family)
            self._images[key] = img
        return img

    def ability_icon(self, ability_id: str) -> pygame.Surface:
        size = (48, 48)
        path = os.path.join(self.settings["paths"]["ability_icons"],
                            f"{ability_id}.png")
        key = (path, size)
        if key in self._images:
            return self._images[key]
        if os.path.isfile(path):
            img = self.load_image(path, size)
        else:
            img = self._icon_with_letter(size, _stable_color(ability_id),
                                         ability_id)
            self._images[key] = img
        return img

    def passive_icon(self, passive_id: str) -> pygame.Surface:
        size = (24, 24)
        path = os.path.join(self.settings["paths"]["passive_icons"],
                            f"{passive_id}.png")
        key = (path, size)
        if key in self._images:
            return self._images[key]
        if os.path.isfile(path):
            img = self.load_image(path, size)
        else:
            img = self._icon_with_letter(size, _stable_color(passive_id),
                                         passive_id)
            self._images[key] = img
        return img