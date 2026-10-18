"""Контракты между слоями. Не содержит логики.

core  → control: Event (см. core/events.py)
control → view:  PresentationCommand
control ← view:  UserInput (клики/кнопки)
control → core:  Action
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------- действия

class ActionKind(str, Enum):
    ATTACK = "attack"
    ABILITY = "ability"      # + ability_id
    MEDITATE = "meditate"


class TargetingKind(str, Enum):
    SELF = "self"
    SINGLE_ENEMY = "single_enemy"
    ALL_ENEMIES = "all_enemies"
    SINGLE_ALLY = "single_ally"
    ALL_ALLIES = "all_allies"
    RANDOM_ADJACENT_ENEMY = "random_adjacent_enemy"


@dataclass(frozen=True)
class Action:
    """То, что control отдаёт в Battle.apply_action()."""
    kind: ActionKind
    actor_slot: int                     # 0..9, индекс героя в объединённом списке
    ability_id: str | None = None
    target_slots: tuple[int, ...] = ()


# ------------------------------------------- команды презентации для view

class PresentationCommandType(str, Enum):
    # Визуальные проигрывания
    PLAY_ATTACK = "play_attack"
    PLAY_HEAL = "play_heal"
    PLAY_APPLY_EFFECT = "play_apply_effect"
    PLAY_REMOVE_EFFECT = "play_remove_effect"
    PLAY_DEATH = "play_death"
    PLAY_MANA_CHANGE = "play_mana_change"
    PLAY_FLOAT_NUMBER = "play_float_number"
    PLAY_TURN_HIGHLIGHT = "play_turn_highlight"

    # Немедленные изменения состояния (без анимации, только снимок)
    REFRESH_SNAPSHOT = "refresh_snapshot"

    # Экранные команды
    SHOW_BATTLE_END = "show_battle_end"


@dataclass(frozen=True)
class PresentationCommand:
    """Что control сообщает view. view не читает core напрямую.

    Координаты слотов и тайминги — ответственность view;
    поля здесь — семантические (slot, family, amount, ...).
    """
    type: PresentationCommandType
    payload: dict[str, Any] = field(default_factory=dict)


# -------------------------------------------- снимок состояния для view

@dataclass(frozen=True)
class EffectView:
    effect_id: str
    family: str
    name: str
    category: str                    # stat_mod / dot / on_damage / action_block
    rounds_left: int
    stacks: int
    description: str
    is_buff: bool


@dataclass(frozen=True)
class HeroView:
    slot: int
    hero_id: str
    name: str
    team: int                        # 0 верх, 1 низ
    hp: int
    hp_max: int
    mana: int
    mana_max: int
    alive: bool
    effects: tuple[EffectView, ...]


@dataclass(frozen=True)
class BattleSnapshot:
    heroes: tuple[HeroView, ...]     # ровно 10 в стабильном порядке слотов 0..9
    active_slot: int | None
    round_number: int
    winner_team: int | None          # None пока бой идёт; в конце — победитель или None (ничья)
    available_actions: tuple[ActionKind, ...]  # что доступно активному герою


# ---------------------------------------------------------- ввод от view

class InputKind(str, Enum):
    CLICK_ACTION = "click_action"     # payload: ability_id or action kind
    CLICK_TARGET = "click_target"     # payload: slot
    CLICK_CANCEL = "click_cancel"
    CLICK_SKIP_ANIM = "click_skip_anim"
    CLICK_MENU = "click_menu"


@dataclass(frozen=True)
class UserInput:
    kind: InputKind
    payload: dict[str, Any] = field(default_factory=dict)