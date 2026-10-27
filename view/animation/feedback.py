"""Числа, лечение, полёт значка эффекта, мана."""
from __future__ import annotations

import pygame

from view.animation.base import Animation
from view.theme import COLORS


class FloatNumberAnimation(Animation):
    def __init__(self, pos, text: str, color, font: pygame.font.Font,
                 duration: float = 0.9, delay: float = 0.0,
                 with_burst: bool = True):
        super().__init__(duration, delay)
        self.start_pos = pos
        self.text = text
        self.color = color
        self.font = font
        self.with_burst = with_burst

    def draw(self, surface: pygame.Surface) -> None:
        if self.finished or self.delay > 0:
            return
        t = self.progress

        if self.with_burst and t < 0.35:
            bt = t / 0.35
            radius = int(14 + 26 * bt)
            alpha = int(180 * (1.0 - bt))
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color, alpha),
                               (radius, radius), radius, 2)
            surface.blit(surf, (self.start_pos[0] - radius,
                                self.start_pos[1] - radius))

        y_offset = -55 * t
        alpha = int(255 * (1.0 - t * t))
        txt = self.font.render(self.text, True, self.color)
        txt.set_alpha(max(0, alpha))
        rect = txt.get_rect(center=(self.start_pos[0],
                                    self.start_pos[1] + y_offset))
        surface.blit(txt, rect)


class HealGlowAnimation(Animation):
    def __init__(self, pos, duration: float = 0.6, delay: float = 0.0):
        super().__init__(duration, delay)
        self.pos = pos

    def draw(self, surface: pygame.Surface) -> None:
        if self.finished or self.delay > 0:
            return
        t = self.progress
        radius = int(22 + 45 * t)
        alpha = max(0, int(190 * (1.0 - t)))
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*COLORS["heal_number"], alpha),
                           (radius, radius), radius)
        surface.blit(surf, (self.pos[0] - radius, self.pos[1] - radius))


class ApplyEffectAnimation(Animation):
    def __init__(self, end_pos, icon: pygame.Surface,
                 duration: float = 0.4, delay: float = 0.0):
        super().__init__(duration, delay)
        self.end_pos = end_pos
        self.icon = icon
        self.start_pos = (end_pos[0], 40)

    def draw(self, surface: pygame.Surface) -> None:
        if self.finished or self.delay > 0:
            return
        t = self.progress
        x = self.start_pos[0] + (self.end_pos[0] - self.start_pos[0]) * t
        y = self.start_pos[1] + (self.end_pos[1] - self.start_pos[1]) * t
        rect = self.icon.get_rect(center=(int(x), int(y)))
        surface.blit(self.icon, rect)


class RemoveEffectAnimation(Animation):
    def __init__(self, pos, icon: pygame.Surface,
                 duration: float = 0.3, delay: float = 0.0):
        super().__init__(duration, delay)
        self.pos = pos
        self.icon = icon

    def draw(self, surface: pygame.Surface) -> None:
        if self.finished or self.delay > 0:
            return
        t = self.progress
        alpha = max(0, int(255 * (1.0 - t)))
        copy = self.icon.copy()
        copy.set_alpha(alpha)
        rect = copy.get_rect(center=self.pos)
        surface.blit(copy, rect)


class ManaPulseAnimation(Animation):
    def __init__(self, rect, duration: float = 0.4, delay: float = 0.0):
        super().__init__(duration, delay)
        self.rect = pygame.Rect(rect)

    def draw(self, surface: pygame.Surface) -> None:
        if self.finished or self.delay > 0:
            return
        t = self.progress
        alpha = max(0, int(220 * (1.0 - t)))
        surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        surf.fill((*COLORS["mana"], alpha))
        surface.blit(surf, self.rect.topleft)