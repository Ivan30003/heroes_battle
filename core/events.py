"""Каталог событий, которые core публикует после каждого действия.

View НЕ читает эти события напрямую — их переводит в PresentationCommand
слой control (см. control/presenter.py, появится в M2).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    BATTLE_START = "battle_start"
    ROUND_START = "round_start"
    TURN_START = "turn_start"
    TURN_END = "turn_end"

    ATTACK = "attack"                     # {attacker, target, percent}
    DAMAGE = "damage"                     # {source, target, amount, is_crit, is_reflected, damage_type}
    MISS = "miss"                         # {attacker, target}
    DODGE = "dodge"                       # {attacker, target}
    HEAL = "heal"                         # {source, target, amount}
    MANA_GAIN = "mana_gain"               # {hero, amount, reason}
    MANA_SPENT = "mana_spent"             # {hero, amount, reason}

    EFFECT_APPLIED = "effect_applied"     # {target, effect_id, family, duration, stacks}
    EFFECT_REPLACED = "effect_replaced"   # {target, effect_id, family}
    EFFECT_EXPIRED = "effect_expired"     # {target, effect_id, family}
    EFFECT_CLEANSED = "effect_cleansed"   # {target, effect_id, family}
    EFFECT_TICK = "effect_tick"           # {target, effect_id, family, damage}

    MEDITATE = "meditate"                 # {hero, mana_gained}
    DEATH = "death"                       # {hero}
    MADNESS_ACTION = "madness_action"     # {hero, action, target}

    ROUND_END = "round_end"               # {}
    BATTLE_END = "battle_end"             # {winner_team: int | None}  None = ничья


@dataclass(frozen=True)
class Event:
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)