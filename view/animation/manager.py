"""Менеджер активных анимаций."""
from __future__ import annotations

import pygame

from view.animation.base import Animation


class AnimationManager:
    def __init__(self):
        self.active: list[Animation] = []

    def add(self, anim: Animation) -> None:
        self.active.append(anim)

    def count(self) -> int:
        return len(self.active)

    def clear(self) -> None:
        self.active.clear()

    def update(self, dt: float) -> None:
        for anim in self.active:
            anim.update(dt)
        self.active = [a for a in self.active if not a.finished]

    def draw(self, surface: pygame.Surface) -> None:
        for anim in self.active:
            anim.draw(surface)