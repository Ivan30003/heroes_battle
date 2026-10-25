"""Эвристический AI. Детерминирован, никакой случайности.

ВАЖНО: actor_slot — это координата слота (0-4 верх, 5-9 низ).
Доступ к герою — только через battle.hero_at(slot).
"""
from __future__ import annotations

from core.battle import Battle
from core.contracts import Action, ActionKind, TargetingKind
from core.effect import EffectCategory
from core.stats import damage_taken_mult, effective_stat, is_mad, is_stunned


class SimpleAI:
    def choose_action(self, battle: Battle, actor_slot: int) -> Action:
        actor = battle.hero_at(actor_slot)
        if not actor.alive or is_stunned(actor) or is_mad(actor):
            return Action(ActionKind.MEDITATE, actor_slot)

        available = battle.available_actions(actor_slot)
        if not available:
            return Action(ActionKind.MEDITATE, actor_slot)

        if ActionKind.ABILITY in available and actor.hp < actor.template.hp * 0.3:
            heal = self._find_heal(battle, actor_slot)
            if heal:
                return heal

        if ActionKind.ABILITY in available:
            kill = self._find_kill(battle, actor_slot)
            if kill:
                return kill
            aoe = self._find_aoe(battle, actor_slot)
            if aoe:
                return aoe

        attack = self._attack_weakest(battle, actor_slot)
        if attack:
            return attack

        return Action(ActionKind.MEDITATE, actor_slot)

    def _find_heal(self, battle: Battle, actor_slot: int) -> Action | None:
        for aid in battle.available_abilities(actor_slot):
            if not self._is_heal_ability(battle, aid):
                continue
            targets = battle.valid_targets(actor_slot, aid)
            if not targets:
                continue
            ally_heroes = [battle.hero_at(t) for t in targets]
            ally_heroes = [h for h in ally_heroes if h is not None]
            if not ally_heroes:
                continue
            hurt = min(ally_heroes,
                       key=lambda h: h.hp / max(h.template.hp, 1))
            return Action(ActionKind.ABILITY, actor_slot,
                          ability_id=aid, target_slots=(hurt.slot,))
        return None

    def _find_kill(self, battle: Battle, actor_slot: int) -> Action | None:
        actor = battle.hero_at(actor_slot)
        for aid in battle.available_abilities(actor_slot):
            ability = battle.abilities[aid]
            if ability.targeting != TargetingKind.SINGLE_ENEMY:
                continue
            if ability.damage_percent <= 0:
                continue
            for t in battle.valid_targets(actor_slot, aid):
                target = battle.hero_at(t)
                if target is None:
                    continue
                est = self._estimate_damage(battle, actor, target,
                                            ability.damage_percent)
                if est >= target.hp:
                    return Action(ActionKind.ABILITY, actor_slot,
                                  ability_id=aid, target_slots=(t,))
        return None

    def _find_aoe(self, battle: Battle, actor_slot: int) -> Action | None:
        actor = battle.hero_at(actor_slot)
        enemies = [h for h in battle.heroes
                   if h.team != actor.team and h.alive]
        if len(enemies) < 2:
            return None
        for aid in battle.available_abilities(actor_slot):
            ability = battle.abilities[aid]
            if ability.targeting != TargetingKind.ALL_ENEMIES:
                continue
            if ability.damage_percent <= 0:
                continue
            total = sum(self._estimate_damage(battle, actor, e,
                                              ability.damage_percent)
                        for e in enemies)
            if total > 0:
                return Action(ActionKind.ABILITY, actor_slot, ability_id=aid)
        return None

    def _attack_weakest(self, battle: Battle,
                        actor_slot: int) -> Action | None:
        targets = battle.valid_targets(actor_slot)
        if not targets:
            return None
        hero_targets = [battle.hero_at(t) for t in targets]
        hero_targets = [h for h in hero_targets if h is not None]
        if not hero_targets:
            return None
        weakest = min(hero_targets, key=lambda h: h.hp)
        return Action(ActionKind.ATTACK, actor_slot,
                      target_slots=(weakest.slot,))

    @staticmethod
    def _estimate_damage(battle: Battle, attacker, target,
                         percent: float) -> float:
        atk = effective_stat(attacker, "attack")
        dfn = effective_stat(target, "defense")
        base = battle.NORM_CONST * (atk / max(dfn, 1.0)) * (percent / 100.0)
        base *= (1.0 + damage_taken_mult(target))
        return base

    @staticmethod
    def _is_heal_ability(battle: Battle, aid: str) -> bool:
        ability = battle.abilities[aid]
        for ref in ability.effect_specs:
            if battle.effects[ref.effect_id].category == EffectCategory.INSTANT_HEAL:
                return True
        return False