"""Расчёт эффективных атрибутов героя с учётом эффектов и пассивок."""
from __future__ import annotations
from core.effect import EffectCategory, EffectSpec
from core.hero import Hero


DEFENSE_FLOOR_RATIO = 0.3


def effective_stat(hero: Hero, stat: str) -> float:
    """Эффективный атрибут с учётом SET / MULT / ADD модификаторов.

    Приоритет:
    1. Если есть хоть один STAT_MOD с ключом "set" для этого stat —
       значение base становится равным последнему set (перебираем в порядке
       наложения, последний выигрывает). MULT/ADD игнорируются.
    2. Иначе применяются MULT и ADD.
    3. В конце — floor защиты (30% от базовой) и кап уклонения/крита (1.0).
    """
    base = float(getattr(hero.template, stat, 0.0))

    set_value: float | None = None
    for eff in hero.effects:
        if eff.spec.category != EffectCategory.STAT_MOD:
            continue
        if eff.spec.payload.get("stat") != stat:
            continue
        if "set" in eff.spec.payload:
            set_value = float(eff.spec.payload["set"])

    if set_value is not None:
        base = set_value
    else:
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


def is_positive_effect(spec: EffectSpec) -> bool:
    """Положительный ли эффект. Используется jinx и цветом иконки.

    - INSTANT_HEAL — положительный.
    - DOT, ACTION_BLOCK — отрицательный.
    - STAT_MOD:
        * с ключом "set" — отрицательный (этот приём всегда "ставит"
          значение, обычно это нерф, а для джинкса безопасно не считать);
        * иначе — положительный, если все числовые значения >= 0.
    - Всё остальное — положительное по умолчанию.
    """
    if spec.category == EffectCategory.INSTANT_HEAL:
        return True
    if spec.category in (EffectCategory.DOT, EffectCategory.ACTION_BLOCK):
        return False
    if spec.category == EffectCategory.STAT_MOD:
        if "set" in spec.payload:
            return False
        numeric = [v for v in spec.payload.values()
                   if isinstance(v, (int, float))]
        return all(v >= 0 for v in numeric) if numeric else True
    return True


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