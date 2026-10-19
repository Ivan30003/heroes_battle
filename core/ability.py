"""Способность: спецификация из JSON."""
from __future__ import annotations
from dataclasses import dataclass
from core.contracts import TargetingKind


@dataclass(frozen=True)
class EffectSpecRef:
    effect_id: str
    applies_to: str

    @classmethod
    def from_dict(cls, d: dict) -> "EffectSpecRef":
        return cls(effect_id=d["effect_id"], applies_to=d["applies_to"])


@dataclass(frozen=True)
class AbilityTemplate:
    id: str
    name: str
    description: str
    mana_cost: int
    targeting: TargetingKind
    damage_percent: float
    cooldown: int
    effect_specs: tuple[EffectSpecRef, ...]

    @classmethod
    def from_dict(cls, d: dict) -> "AbilityTemplate":
        return cls(
            id=d["id"], name=d["name"], description=d["description"],
            mana_cost=int(d["mana_cost"]),
            targeting=TargetingKind(d["targeting"]),
            damage_percent=float(d["damage_percent"]),
            cooldown=int(d.get("cooldown", 0)),
            effect_specs=tuple(EffectSpecRef.from_dict(s) for s in d.get("effect_specs", [])),
        )