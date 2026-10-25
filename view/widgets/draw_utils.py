"""Общие примитивы рисования."""
from __future__ import annotations

import pygame


def octagon_points(rect: pygame.Rect, bevel: int) -> list[tuple[int, int]]:
    """Прямоугольник со скошенными углами — 8 вершин."""
    x, y, w, h = rect.x, rect.y, rect.w, rect.h
    return [
        (x + bevel, y),
        (x + w - bevel, y),
        (x + w, y + bevel),
        (x + w, y + h - bevel),
        (x + w - bevel, y + h),
        (x + bevel, y + h),
        (x, y + h - bevel),
        (x, y + bevel),
    ]


def draw_beveled_rect(surface: pygame.Surface, color, rect: pygame.Rect,
                      bevel: int = 6, border_color=None,
                      border_width: int = 0) -> None:
    points = octagon_points(rect, bevel)
    pygame.draw.polygon(surface, color, points)
    if border_width > 0 and border_color is not None:
        pygame.draw.polygon(surface, border_color, points, border_width)