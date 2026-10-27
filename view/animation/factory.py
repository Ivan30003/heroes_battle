"""PresentationCommand → Animation (или None для мгновенных команд)."""
from __future__ import annotations

import pygame

from control.public_api import PresentationCommandType
from view.animation.attacks import (
    HitSparkAnimation, ProjectileAnimation, TurnHighlightAnimation,
)
from view.animation.feedback import (
    ApplyEffectAnimation, FloatNumberAnimation, HealGlowAnimation,
    ManaPulseAnimation, RemoveEffectAnimation,
)
from view.theme import COLORS


def create_animation(command, slot_rects, theme, assets):
    t = command.type
    p = command.payload

    if t == PresentationCommandType.PLAY_ATTACK:
        src = slot_rects[p["attacker"]].center
        dst = slot_rects[p["target"]].center
        return ProjectileAnimation(src, dst, color=COLORS["accent"])

    if t == PresentationCommandType.PLAY_HEAL:
        pos = slot_rects[p["slot"]].center
        return HealGlowAnimation(pos)

    if t == PresentationCommandType.PLAY_APPLY_EFFECT:
        pos = slot_rects[p["slot"]].center
        icon = assets.effect_icon(p["family"])
        return ApplyEffectAnimation(pos, icon)

    if t == PresentationCommandType.PLAY_REMOVE_EFFECT:
        pos = slot_rects[p["slot"]].center
        icon = assets.effect_icon(p["family"])
        return RemoveEffectAnimation(pos, icon)

    if t == PresentationCommandType.PLAY_FLOAT_NUMBER:
        pos = slot_rects[p["slot"]].center
        color, text, size, delay = _format_number(p["kind"], p["value"])
        font = theme.font(size, bold=True)
        return FloatNumberAnimation(pos, text, color, font, delay=delay)

    if t == PresentationCommandType.PLAY_MANA_CHANGE:
        rect = slot_rects[p["slot"]]
        mana_rect = pygame.Rect(rect.x + 4, rect.bottom - 22,
                                rect.width - 8, 6)
        return ManaPulseAnimation(mana_rect)

    if t == PresentationCommandType.PLAY_TURN_HIGHLIGHT:
        if p.get("madness"):
            return None
        rect = slot_rects[p["slot"]]
        return TurnHighlightAnimation(rect, bevel=8)

    if t == PresentationCommandType.PLAY_DEATH:
        pos = slot_rects[p["slot"]].center
        return HitSparkAnimation(pos, color=COLORS["hp"], duration=0.55)

    # REFRESH_SNAPSHOT, SHOW_BATTLE_END — обрабатываются на уровне экрана
    return None


def _format_number(kind: str, value: int):
    """(color, text, size, delay)."""
    if kind == "miss":
        return COLORS["miss_number"], "Промах", 22, 0.15
    if kind == "crit":
        return COLORS["crit_number"], f"-{value}", 42, 0.20
    if kind == "heal":
        return COLORS["heal_number"], f"+{value}", 30, 0.0
    if kind == "reflected":
        return COLORS["control"], f"-{value}", 24, 0.10
    if kind == "dot":
        return COLORS["dot"], f"-{value}", 22, 0.10
    if kind == "mana":
        return COLORS["mana"], f"+{value}", 24, 0.0
    return COLORS["text"], f"-{value}", 28, 0.10