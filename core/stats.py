"""Расчёт эффективных атрибутов героя с учётом эффектов и пассивок."""
from __future__ import annotations
from core.effect import EffectCategory
from core.hero import Hero


DEFENSE_FLOOR_RATIO = 0.3


def effective_stat(hero: Hero, stat: str) -> float:
    base = float(getattr(hero.template, stat, 0.0))
    for eff in hero.effects:
        if eff.spec.category != EffectCategory.STAT_MOD:
            continue
        if eff.spec.payload.get("stat") != stat:
            continue
        if "mult" in eff.spec.payload:
            base *= (1.0 + float(eff.spec.payload["mult"]))
        if "add" in eff.spec.payload:
            base += float(eff.spec.payload["add"])

    if stat == "defense":
        base = max(base, hero.template.defense * DEFENSE_FLOOR_RATIO)
    if stat in ("dodge", "crit"):
        base = min(base, 1.0)
    return base


def accuracy_penalty_eff(hero: Hero) -> float:
    if hero.has_passive("blind_immunity"):
        return 0.0
    penalty = 0.0
    for eff in hero.effects:
        if eff.spec.category == EffectCategory.STAT_MOD and \
           eff.spec.payload.get("stat") == "accuracy_penalty":
            penalty += float(eff.spec.payload.get("add", 0.0))
    return min(penalty, 1.0)


def damage_taken_mult(hero: Hero) -> float:
    total = 0.0
    for eff in hero.effects:
        total += float(eff.spec.payload.get("damage_taken_mult", 0.0))
    return total


def is_stunned(hero: Hero) -> bool:
    return any(e.family == "stun" for e in hero.effects)


def is_silenced(hero: Hero) -> bool:
    return any(e.family == "silence" for e in hero.effects)


def is_mad(hero: Hero) -> bool:
    return any(e.family == "madness" for e in hero.effects)