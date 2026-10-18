"""Загрузчик ассетов с graceful-фолбэком на плейсхолдеры."""
from __future__ import annotations

import os
from typing import Any

import pygame


class AssetManager:
    def __init__(self, settings: dict[str, Any]):
        self.settings = settings
        self._images: dict[tuple, pygame.Surface] = {}

    def load_image(
        self, path: str, size: tuple[int, int] | None = None
    ) -> pygame.Surface:
        key = (path, size)
        if key in self._images:
            return self._images[key]

        if path and os.path.isfile(path):
            img = pygame.image.load(path).convert_alpha()
            if size is not None and img.get_size() != size:
                img = pygame.transform.smoothscale(img, size)
        else:
            img = self._placeholder(size or (32, 32), os.path.basename(path or "?"))

        self._images[key] = img
        return img

    @staticmethod
    def _placeholder(size: tuple[int, int], label: str) -> pygame.Surface:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((80, 60, 90, 220))
        pygame.draw.rect(surf, (200, 120, 220), surf.get_rect(), 2)
        return surf

    # ---------- семантические загрузчики ----------

    def hero_portrait(self, sprite_rel_path: str) -> pygame.Surface:
        ui = self.settings["ui"]
        full = os.path.join(self.settings["paths"]["sprites"], os.path.basename(sprite_rel_path))
        return self.load_image(full, (ui["slot_width"], ui["slot_height"]))

    def effect_icon(self, family: str) -> pygame.Surface:
        size = self.settings["ui"]["effect_icon_size"]
        path = os.path.join(self.settings["paths"]["effect_icons"], f"{family}.png")
        return self.load_image(path, (size, size))

    def ability_icon(self, ability_id: str) -> pygame.Surface:
        path = os.path.join(self.settings["paths"]["ability_icons"], f"{ability_id}.png")
        return self.load_image(path, (48, 48))

    def passive_icon(self, passive_id: str) -> pygame.Surface:
        path = os.path.join(self.settings["paths"]["passive_icons"], f"{passive_id}.png")
        return self.load_image(path, (24, 24))