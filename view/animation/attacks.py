"""Снаряд, удар-вспышка, поворот-подсветка."""
from __future__ import annotations

import pygame

from view.animation.base import Animation
from view.theme import COLORS
from view.widgets.draw_utils import octagon_points


class ProjectileAnimation(Animation):
    def __init__(self, start_pos, end_pos, color=None,
                 duration: float = 0.28, delay: float = 0.0):
        super().__init__(duration, delay)
        self.start = start_pos
        self.end = end_pos
        self.color = color or COLORS["accent"]

    def draw(self, surface: pygame.Surface) -> None:
        if self.finished or self.delay > 0:
            return
        t = self.progress
        x = self.start[0] + (self.end[0] - self.start[0]) * t
        y = self.start[1] + (self.end[1] - self.start[1]) * t
        pygame.draw.circle(surface, self.color, (int(x), int(y)), 9)
        pygame.draw.circle(surface, (255, 255, 255), (int(x), int(y)), 4)


class HitSparkAnimation(Animation):
    def __init__(self, pos, color, duration: float = 0.35,
                 delay: float = 0.0):
        super().__init__(duration, delay)
        self.pos = pos
        self.color = color

    def draw(self, surface: pygame.Surface) -> None:
        if self.finished or self.delay > 0:
            return
        t = self.progress
        radius = int(12 + 28 * t)
        alpha = max(0, int(220 * (1.0 - t)))
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (radius, radius),
                           radius, 2)
        surface.blit(surf, (self.pos[0] - radius, self.pos[1] - radius))


class TurnHighlightAnimation(Animation):
    def __init__(self, rect, bevel: int, duration: float = 0.4,
                 delay: float = 0.0):
        super().__init__(duration, delay)
        self.rect = pygame.Rect(rect)
        self.bevel = bevel

    def draw(self, surface: pygame.Surface) -> None:
        if self.finished or self.delay > 0:
            return
        t = self.progress
        alpha = max(0, int(255 * (1.0 - t) * (1.0 - t)))
        overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pts = octagon_points(pygame.Rect(0, 0, *self.rect.size), self.bevel)
        pygame.draw.polygon(overlay, (*COLORS["accent"], alpha), pts, 4)
        surface.blit(overlay, self.rect.topleft)