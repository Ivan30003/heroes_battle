"""Контракты между слоями. Не содержит логики."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionKind(str, Enum):
    ATTACK = "attack"
    ABILITY = "ability"
    MEDITATE = "meditate"


class TargetingKind(str, Enum):
    SELF = "SELF"
    SINGLE_ENEMY = "SINGLE_ENEMY"
    ALL_ENEMIES = "ALL_ENEMIES"
    SINGLE_ALLY = "SINGLE_ALLY"
    ALL_ALLIES = "ALL_ALLIES"
    RANDOM_ADJACENT_ENEMY = "RANDOM_ADJACENT_ENEMY"


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    actor_slot: int
    ability_id: str | None = None
    target_slots: tuple[int, ...] = ()


class PresentationCommandType(str, Enum):
    PLAY_ATTACK = "play_attack"
    PLAY_HEAL = "play_heal"
    PLAY_APPLY_EFFECT = "play_apply_effect"
    PLAY_REMOVE_EFFECT = "play_remove_effect"
    PLAY_DEATH = "play_death"
    PLAY_MANA_CHANGE = "play_mana_change"
    PLAY_FLOAT_NUMBER = "play_float_number"
    PLAY_TURN_HIGHLIGHT = "play_turn_highlight"
    REFRESH_SNAPSHOT = "refresh_snapshot"
    SHOW_BATTLE_END = "show_battle_end"


@dataclass(frozen=True)
class PresentationCommand:
    type: PresentationCommandType
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EffectView:
    effect_id: str
    family: str
    name: str
    category: str
    rounds_left: int
    stacks: int
    description: str
    is_buff: bool


@dataclass(frozen=True)
class HeroView:
    slot: int
    hero_id: str
    name: str
    team: int
    hp: int
    hp_max: int
    mana: int
    mana_max: int
    alive: bool
    effects: tuple[EffectView, ...]


@dataclass(frozen=True)
class BattleSnapshot:
    heroes: tuple[HeroView, ...]
    active_slot: int | None
    round_number: int
    winner_team: int | None
    available_actions: tuple[ActionKind, ...]


class InputKind(str, Enum):
    CLICK_ACTION = "click_action"
    CLICK_TARGET = "click_target"
    CLICK_CANCEL = "click_cancel"
    CLICK_SKIP_ANIM = "click_skip_anim"
    CLICK_MENU = "click_menu"


@dataclass(frozen=True)
class UserInput:
    kind: InputKind
    payload: dict[str, Any] = field(default_factory=dict)