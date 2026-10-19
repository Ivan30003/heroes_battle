"""Эффекты: спецификация из JSON + активный экземпляр."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any


class EffectCategory(str, Enum):
    STAT_MOD = "STAT_MOD"
    DOT = "DOT"
    ON_DAMAGE_TAKEN = "ON_DAMAGE_TAKEN"
    ACTION_BLOCK = "ACTION_BLOCK"
    INSTANT_DAMAGE = "INSTANT_DAMAGE"
    INSTANT_HEAL = "INSTANT_HEAL"
    INSTANT_CLEANSE = "INSTANT_CLEANSE"


class DurationType(str, Enum):
    ROUNDS = "ROUNDS"
    INSTANT = "INSTANT"


@dataclass(frozen=True)
class EffectSpec:
    id: str
    family: str
    name: str
    category: EffectCategory
    duration_type: DurationType
    duration: int
    dispellable: bool
    stackable: bool
    payload: dict[str, Any]

    @classmethod
    def from_dict(cls, d: dict) -> "EffectSpec":
        return cls(
            id=d["id"], family=d["family"], name=d["name"],
            category=EffectCategory(d["category"]),
            duration_type=DurationType(d["duration_type"]),
            duration=d["duration"],
            dispellable=d["dispellable"],
            stackable=d["stackable"],
            payload=dict(d["payload"]),
        )


@dataclass
class Effect:
    spec: EffectSpec
    source_slot: int
    duration_left: int

    @property
    def family(self) -> str:
        return self.spec.family