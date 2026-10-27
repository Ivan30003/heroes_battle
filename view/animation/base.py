"""Базовая анимация: длительность, задержка, прогресс, draw()."""
from __future__ import annotations

import pygame


class Animation:
    def __init__(self, duration: float, delay: float = 0.0):
        self.duration = max(duration, 0.0001)
        self.delay = max(delay, 0.0)
        self.elapsed = 0.0
        self.finished = False

    def update(self, dt: float) -> None:
        if self.finished:
            return
        if self.delay > 0:
            self.delay -= dt
            if self.delay > 0:
                return
            dt = -self.delay          # перетекание «переполнения» в elapsed
            self.delay = 0.0
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.elapsed = self.duration
            self.finished = True

    @property
    def progress(self) -> float:
        return min(1.0, self.elapsed / self.duration)

    def draw(self, surface: pygame.Surface) -> None:
        pass