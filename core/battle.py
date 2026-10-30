"""Боевой цикл. Единственный источник истины."""
from __future__ import annotations

import random
from typing import Any, Iterable

from core.contracts import (
    Action, ActionKind, BattleSnapshot, EffectView, HeroView, TargetingKind,
)
from core.events import Event, EventType
from core.hero import Hero, HeroTemplate
from core.ability import AbilityTemplate
from core.effect import Effect, EffectSpec, EffectCategory
from core.stats import (
    effective_stat, accuracy_penalty_eff, damage_taken_mult,
    is_stunned, is_silenced, is_mad, is_positive_effect,
)


AURA_FAMILIES = frozenset({"attack_up_aura"})


class Battle:
    def __init__(
        self,
        top_heroes: list[HeroTemplate],
        bottom_heroes: list[HeroTemplate],
        abilities: dict[str, AbilityTemplate],
        effects: dict[str, EffectSpec],
        passives: set[str],
        settings: dict[str, Any],
        seed: int | None = None,
    ):
        self.abilities = abilities
        self.effects = effects
        self.passives = passives
        self.settings = settings
        self.NORM_CONST = float(settings["combat"]["norm_const"])
        self.MAX_MANA = int(settings["combat"]["max_mana"])
        self.rng = random.Random(seed)

        self.heroes: list[Hero] = []
        for i, tpl in enumerate(top_heroes):
            self.heroes.append(Hero(template=tpl, team=0, slot_in_team=i, slot=i))
        for i, tpl in enumerate(bottom_heroes):
            self.heroes.append(Hero(template=tpl, team=1, slot_in_team=i, slot=5 + i))

        # slot ID (0-4 - верх, 5-9 - низ) -> Hero.
        # Обязательно для боёв меньше 5×5: list index != slot ID.
        self._by_slot: dict[int, Hero] = {h.slot: h for h in self.heroes}

        # Группы A/B теперь хранят slot ID, а не list index.
        all_slots = [h.slot for h in self.heroes]
        self.rng.shuffle(all_slots)
        half = (len(all_slots) + 1) // 2
        self.group_a = all_slots[:half]
        self.group_b = all_slots[half:]

        # Стартовая мана (пассивка start_mana_1 и т. п.)
        for h in self.heroes:
            if h.has_passive("start_mana_1"):
                h.mana = min(h.mana + 1, self.MAX_MANA)

        self.round_number = 0
        self.current_order: list[int] = []
        self.current_idx = -1
        self._over = False
        self._winner: int | None = None

    # ------------------------------------------------------------ lifecycle

    def start(self) -> list[Event]:
        events = [Event(EventType.BATTLE_START, {})]

        # Пассивка command_aura: на старте боя наложить ауру на всех живых
        # союзников (включая самого командора). Аура переживёт смерть
        # источника только до его смерти — снимается в _handle_death.
        for hero in self.heroes:
            if hero.alive and hero.has_passive("command_aura"):
                spec = self.effects["attack_up_aura_10"]
                for ally in self.heroes:
                    if ally.team == hero.team and ally.alive:
                        # применяем без триггера positive_effect_heal,
                        # чтобы не было "лечения на старте"
                        ally.effects.append(Effect(
                            spec=spec, source_slot=hero.slot,
                            duration_left=spec.duration,
                        ))
                        events.append(Event(EventType.EFFECT_APPLIED, {
                            "slot": ally.slot,
                            "effect_id": spec.id,
                            "family": spec.family,
                            "duration": spec.duration,
                        }))

        events.extend(self._start_round())
        events.extend(self._advance_to_actor())
        return events

    def _start_round(self) -> list[Event]:
        self.round_number += 1
        group = self.group_a if self.round_number % 2 == 1 else self.group_b
        alive = [s for s in group if self._by_slot[s].alive]
        self.rng.shuffle(alive)
        self.current_order = alive
        self.current_idx = -1
        for h in self.heroes:
            h.flags["used_ability_this_round"] = False
        return [Event(EventType.ROUND_START, {"round": self.round_number})]

    def _advance_to_actor(self) -> list[Event]:
        events: list[Event] = []
        while True:
            self.current_idx += 1
            if self.current_idx >= len(self.current_order):
                events.extend(self._resolve_round_end())
                if self._over:
                    events.append(Event(EventType.BATTLE_END, {"winner": self._winner}))
                    return events
                events.extend(self._start_round())
                continue

            actor_slot = self.current_order[self.current_idx]
            actor = self._by_slot[actor_slot]
            events.append(Event(EventType.TURN_START, {"slot": actor_slot}))

            if not actor.alive or is_stunned(actor):
                events.append(Event(EventType.TURN_END, {
                    "slot": actor_slot, "skipped": "stun" if actor.alive else "dead",
                }))
                continue

            return events

    def _resolve_round_end(self) -> list[Event]:
        events: list[Event] = []

        # 1) DOT tick
        for hero in self.heroes:
            if not hero.alive:
                continue
            for eff in list(hero.effects):
                if eff.spec.category != EffectCategory.DOT:
                    continue
                dmg = int(eff.spec.payload.get("damage", 0))
                if dmg <= 0:
                    continue
                hero.hp -= dmg
                events.append(Event(EventType.EFFECT_TICK, {
                    "slot": hero.slot, "effect_id": eff.spec.id,
                    "family": eff.family, "damage": dmg,
                }))
                if not hero.alive:
                    events.append(Event(EventType.DEATH, {"slot": hero.slot}))
                    hero.effects.clear()
                    break

        # 2) Проверка смертей
        self._check_battle_end()
        if self._over:
            events.append(Event(EventType.ROUND_END, {"round": self.round_number}))
            return events

        # 3) mana_font
        for hero in self.heroes:
            if not hero.alive or not hero.has_passive("mana_font"):
                continue
            allies = [h for h in self.heroes if h.team == hero.team and h.alive]
            if not allies:
                continue
            max_atk = max(effective_stat(h, "attack") for h in allies)
            candidates = [h for h in allies if effective_stat(h, "attack") == max_atk]
            chosen = self.rng.choice(candidates)
            events.extend(self._gain_mana(chosen, 1, reason="mana_font"))

        # 4) +1 маны всем живым
        for hero in self.heroes:
            if hero.alive:
                events.extend(self._gain_mana(hero, 1, reason="round_end"))

        # 4.5) Round-end passives
        for hero in self.heroes:
            if not hero.alive:
                continue
            if (hero.has_passive("discipline")
                    and not hero.flags.get("used_ability_this_round", False)):
                events.extend(self._apply_effect(
                    hero, self.effects["defense_up_10_2r"], hero.slot))

        # 5) Уменьшение длительностей
        for hero in self.heroes:
            if not hero.alive:
                continue
            for eff in list(hero.effects):
                eff.duration_left -= 1
                if eff.duration_left <= 0:
                    hero.effects.remove(eff)
                    events.append(Event(EventType.EFFECT_EXPIRED, {
                        "slot": hero.slot, "effect_id": eff.spec.id,
                        "family": eff.family,
                    }))

        # 6) Финальная проверка победы
        self._check_battle_end()
        events.append(Event(EventType.ROUND_END, {"round": self.round_number}))
        return events

    def _check_battle_end(self) -> bool:
        if self._over:
            return True
        team0 = any(h.alive for h in self.heroes if h.team == 0)
        team1 = any(h.alive for h in self.heroes if h.team == 1)
        if team0 and team1:
            return False
        self._over = True
        if not team0 and not team1:
            self._winner = None
        elif not team0:
            self._winner = 1
        else:
            self._winner = 0
        return True

    def _handle_death(self, hero: Hero) -> list[Event]:
        """Снять с умершего героя все эффекты и его ауры с живых союзников."""
        events: list[Event] = []
        hero.effects.clear()
        for other in self.heroes:
            if not other.alive or other.slot == hero.slot:
                continue
            for eff in list(other.effects):
                if (eff.source_slot == hero.slot
                        and eff.family in AURA_FAMILIES):
                    other.effects.remove(eff)
                    events.append(Event(EventType.EFFECT_EXPIRED, {
                        "slot": other.slot, "effect_id": eff.spec.id,
                        "family": eff.family,
                    }))
        return events
    # ------------------------------------------------------------------ API

    def is_over(self) -> bool:
        return self._over

    def winner(self) -> int | None:
        return self._winner

    def current_actor(self) -> int | None:
        if self._over:
            return None
        if 0 <= self.current_idx < len(self.current_order):
            return self.current_order[self.current_idx]
        return None

    def hero_at(self, slot: int) -> Hero:
        """Герой по координате слота (0-4 верх, 5-9 низ).

        Raises KeyError, если слот не занят (например, бой 3×3 без слота 3).
        """
        return self._by_slot[slot]

    def hero_at_or_none(self, slot: int) -> Hero | None:
        return self._by_slot.get(slot)

    def available_actions(self, actor_slot: int) -> tuple[ActionKind, ...]:
        hero = self._by_slot.get(actor_slot)
        if hero is None or not hero.alive or is_stunned(hero) or is_mad(hero):
            return ()
        if is_silenced(hero):
            return (ActionKind.ATTACK, ActionKind.MEDITATE)
        actions: list[ActionKind] = [ActionKind.ATTACK]
        if self.available_abilities(actor_slot):
            actions.append(ActionKind.ABILITY)
        actions.append(ActionKind.MEDITATE)
        return tuple(actions)

    def available_abilities(self, actor_slot: int) -> tuple[str, ...]:
        hero = self._by_slot.get(actor_slot)
        if hero is None or not hero.alive:
            return ()
        if is_stunned(hero) or is_silenced(hero) or is_mad(hero):
            return ()
        return tuple(
            aid for aid in hero.template.ability_ids
            if hero.mana >= self.abilities[aid].mana_cost
        )

    def valid_targets(self, actor_slot: int,
                      ability_id: str | None = None) -> tuple[int, ...]:
        hero = self._by_slot.get(actor_slot)
        if hero is None:
            return ()
        if ability_id is None:
            return tuple(h.slot for h in self.heroes
                         if h.team != hero.team and h.alive)
        ability = self.abilities[ability_id]
        t = ability.targeting
        if t == TargetingKind.SELF:
            return (actor_slot,)
        if t == TargetingKind.SINGLE_ENEMY:
            return tuple(h.slot for h in self.heroes
                         if h.team != hero.team and h.alive)
        if t == TargetingKind.SINGLE_ALLY:
            return tuple(h.slot for h in self.heroes
                         if h.team == hero.team and h.alive)
        return ()

    def apply_action(self, action: Action) -> list[Event]:
        actor_slot = self.current_actor()
        if actor_slot is None:
            raise RuntimeError("Battle is over or not started")
        if action.actor_slot != actor_slot:
            raise ValueError(f"Not this hero's turn: {action.actor_slot} vs {actor_slot}")

        events: list[Event] = []
        hero = self._by_slot[actor_slot]

        if is_mad(hero):
            action = self._pick_madness_action(hero)
            events.append(Event(EventType.MADNESS_ACTION, {
                "slot": actor_slot, "action": action.kind.value,
                "ability_id": action.ability_id,
                "targets": action.target_slots,
            }))

        events.extend(self._resolve_action(action))
        events.append(Event(EventType.TURN_END, {"slot": actor_slot}))

        if self._check_battle_end():
            events.append(Event(EventType.BATTLE_END, {"winner": self._winner}))
            return events

        events.extend(self._advance_to_actor())
        return events

    # ---------------------------------------------------------- resolution

    def _resolve_action(self, action: Action) -> list[Event]:
        hero = self._by_slot[action.actor_slot]

        if action.kind == ActionKind.ATTACK:
            if not action.target_slots:
                raise ValueError("Attack requires target_slots")
            target_slot = action.target_slots[0]
            events = [Event(EventType.ATTACK, {
                "attacker": action.actor_slot, "target": target_slot, "percent": 100.0,
            })]
            events.extend(self._deal_damage(hero, self._by_slot[target_slot], 100.0))
            events.extend(self._gain_mana(hero, 1, reason="attack"))
            return events

        if action.kind == ActionKind.MEDITATE:
            events = self._gain_mana(hero, 2, reason="meditate")
            events.append(Event(EventType.MEDITATE, {"slot": action.actor_slot}))
            return events

        # ABILITY
        if action.kind != ActionKind.ABILITY or not action.ability_id:
            raise ValueError("Invalid ability action")
        ability = self.abilities[action.ability_id]
        if hero.mana < ability.mana_cost:
            raise ValueError(f"Not enough mana: {hero.mana}/{ability.mana_cost}")
        hero.mana -= ability.mana_cost
        hero.flags["used_ability_this_round"] = True          # ← новая строка
        events = [Event(EventType.MANA_SPENT, {
            "slot": action.actor_slot, "amount": ability.mana_cost,
        })]
        events.extend(self._resolve_ability(hero, ability, list(action.target_slots)))
        return events

    def _resolve_ability(self, caster: Hero, ability: AbilityTemplate,
                         target_slots: list[int]) -> list[Event]:
        events: list[Event] = []

        # Итоговый список первичных целей
        if ability.targeting == TargetingKind.ALL_ENEMIES:
            targets = [h.slot for h in self.heroes if h.team != caster.team and h.alive]
        elif ability.targeting == TargetingKind.ALL_ALLIES:
            targets = [h.slot for h in self.heroes if h.team == caster.team and h.alive]
        elif ability.targeting == TargetingKind.SELF:
            targets = [caster.slot]
        elif ability.targeting == TargetingKind.RANDOM_ADJACENT_ENEMY:
            adj = self._adjacent_enemies(caster)
            targets = [self.rng.choice(adj)] if adj else []
        elif ability.targeting == TargetingKind.ADJACENT_ALLIES:      # ← новый elif
            targets = self._adjacent_allies(caster)
        else:
            targets = list(target_slots)
        targets = sorted(targets)

        if ability.damage_percent > 0:
            for ts in targets:
                events.extend(self._deal_damage(caster, self._by_slot[ts], ability.damage_percent))

        for ref in ability.effect_specs:
            spec = self.effects[ref.effect_id]
            for et in self._resolve_effect_targets(caster, ref.applies_to, targets):
                target = self._by_slot[et]
                if not target.alive:
                    continue
                if spec.category == EffectCategory.INSTANT_DAMAGE:
                    if "percent" in spec.payload:
                        events.extend(self._deal_damage(
                            caster, target, float(spec.payload["percent"])))
                    elif "damage" in spec.payload:
                        events.extend(self._deal_damage(
                            caster, target, 0.0,
                            fixed_amount=int(spec.payload["damage"])))
                    else:
                        raise ValueError(
                            f"INSTANT_DAMAGE effect {spec.id}: "
                            f"нужен ключ 'percent' или 'damage' в payload")
                elif spec.category == EffectCategory.INSTANT_HEAL:
                    amount = int(target.template.hp * float(spec.payload["percent"]))
                    events.extend(self._heal(caster, target, amount))
                elif spec.category == EffectCategory.INSTANT_CLEANSE:
                    events.extend(self._cleanse(target, spec.payload.get("filter", "negative")))
                else:
                    events.extend(self._apply_effect(target, spec, caster.slot))
        return events

    def _resolve_effect_targets(self, caster: Hero, applies_to: str,
                                primary_targets: list[int]) -> list[int]:
        if applies_to == "primary":
            return list(primary_targets)
        if applies_to == "self":
            return [caster.slot]
        if applies_to == "all_targets":
            return list(primary_targets)
        if applies_to == "all_allies":
            return [h.slot for h in self.heroes if h.team == caster.team and h.alive]
        if applies_to == "random_adjacent_enemy":
            adj = self._adjacent_enemies(caster)
            return [self.rng.choice(adj)] if adj else []
        return []

    def _adjacent_enemies(self, caster: Hero) -> list[int]:
        result = []
        enemy_team = 1 - caster.team
        for delta in (-1, 1):
            s = caster.slot_in_team + delta
            if 0 <= s <= 4:
                slot = enemy_team * 5 + s
                if slot in self._by_slot and self._by_slot[slot].alive:
                    result.append(slot)
        return result

    def _adjacent_allies(self, caster: Hero) -> list[int]:
        """Slot ID живых союзников на соседних слотах (slot_in_team +-1)."""
        result = []
        for delta in (-1, 1):
            s = caster.slot_in_team + delta
            if 0 <= s <= 4:
                slot = caster.team * 5 + s
                h = self._by_slot.get(slot)
                if h is not None and h.alive:
                    result.append(slot)
        return result

    def _deal_damage(self, attacker: Hero, target: Hero, percent: float,
                     is_reflected: bool = False, is_counter: bool = False,
                     fixed_amount: int | None = None) -> list[Event]:
        events: list[Event] = []
        if not target.alive:
            return events

        # Уклонение (кроме отражёнки и контрудара)
        if not is_reflected and not is_counter:
            dodge = effective_stat(target, "dodge")
            acc_pen = accuracy_penalty_eff(attacker)
            hit_chance = (1.0 - dodge) * (1.0 - acc_pen)
            if self.rng.random() > hit_chance:
                events.append(Event(EventType.MISS, {
                    "attacker": attacker.slot, "target": target.slot,
                }))
                if target.has_passive("counter_on_miss") and not is_reflected:
                    events.extend(self._deal_damage(target, attacker, 125.0,
                                                    is_counter=True))
                return events

        # Крит — только для нефиксированного урона
        crit = False
        if fixed_amount is None and not is_reflected and not is_counter:
            crit = self.rng.random() < effective_stat(attacker, "crit")

        if fixed_amount is not None:
            base = float(fixed_amount)
        else:
            atk = effective_stat(attacker, "attack")
            dfn = effective_stat(target, "defense")
            base = self.NORM_CONST * (atk / max(dfn, 1.0)) * (percent / 100.0)
            if crit:
                base *= 2.0

        base *= (1.0 + damage_taken_mult(target))

        # Пассивка jinx: +5% финального урона за каждый положительный эффект
        # на цели. Работает и для обычных атак, и для способностей, и для
        # фиксированного урона. Отражённый урон — это входящий для атакующего,
        # поэтому не бустим.
        if not is_reflected and attacker.has_passive("jinx"):
            positive_count = sum(
                1 for e in target.effects if is_positive_effect(e.spec)
            )
            base *= (1.0 + 0.05 * positive_count)

        damage = max(1, int(base))
        target.hp -= damage
        events.append(Event(EventType.DAMAGE, {
            "source": attacker.slot, "target": target.slot,
            "amount": damage, "crit": crit, "reflected": is_reflected,
        }))

        if not target.alive:
            events.append(Event(EventType.DEATH, {"slot": target.slot}))
            events.extend(self._handle_death(target))
            return events

        # Отражение
        if not is_reflected and target.alive:
            for eff in list(target.effects):
                if eff.spec.category != EffectCategory.ON_DAMAGE_TAKEN:
                    continue
                pct = float(eff.spec.payload.get("reflect_percent", 0.0))
                reflect_amt = int(damage * pct)
                if reflect_amt > 0 and attacker.alive:
                    reflect_amt = int(reflect_amt * (1.0 + damage_taken_mult(attacker)))
                    reflect_amt = max(1, reflect_amt)
                    attacker.hp -= reflect_amt
                    events.append(Event(EventType.DAMAGE, {
                        "source": target.slot, "target": attacker.slot,
                        "amount": reflect_amt, "crit": False, "reflected": True,
                    }))
                    if not attacker.alive:
                        events.append(Event(EventType.DEATH,
                                            {"slot": attacker.slot}))
                        events.extend(self._handle_death(attacker))
        return events

    def _heal(self, source: Hero, target: Hero, amount: int) -> list[Event]:
        if not target.alive:
            return []
        actual = min(amount, target.template.hp - target.hp)
        if actual <= 0:
            return []
        target.hp += actual
        return [Event(EventType.HEAL, {
            "source": source.slot, "target": target.slot, "amount": actual,
        })]

    def _cleanse(self, target: Hero, filter_type: str) -> list[Event]:
        events: list[Event] = []
        to_remove: list[Effect] = []
        for eff in target.effects:
            if not eff.spec.dispellable:
                continue
            if filter_type == "negative":
                is_negative = (
                    eff.spec.category in (EffectCategory.DOT, EffectCategory.ACTION_BLOCK)
                    or (eff.spec.category == EffectCategory.STAT_MOD and any(
                        v < 0 for v in eff.spec.payload.values()
                        if isinstance(v, (int, float))))
                )
                if is_negative:
                    to_remove.append(eff)
        for eff in to_remove:
            target.effects.remove(eff)
            events.append(Event(EventType.EFFECT_CLEANSED, {
                "slot": target.slot, "effect_id": eff.spec.id, "family": eff.family,
            }))
        return events

    def _apply_effect(self, target: Hero, spec: EffectSpec, source_slot: int) -> list[Event]:
        events: list[Event] = []
        if not target.alive:
            return events

        if not spec.stackable:
            for eff in list(target.effects):
                if eff.family == spec.family:
                    target.effects.remove(eff)
                    events.append(Event(EventType.EFFECT_REPLACED, {
                        "slot": target.slot, "effect_id": eff.spec.id,
                        "family": eff.family,
                    }))

        target.effects.append(Effect(spec=spec, source_slot=source_slot,
                                     duration_left=spec.duration))
        events.append(Event(EventType.EFFECT_APPLIED, {
            "slot": target.slot, "effect_id": spec.id,
            "family": spec.family, "duration": spec.duration,
        }))

        # Пассивка positive_effect_heal: любой положительный эффект на герое
        # лечит его на 5% от макс. HP.
        if (target.has_passive("positive_effect_heal")
                and self._is_buff(spec)):
            heal_amount = max(1, int(target.template.hp * 0.05))
            events.extend(self._heal(target, target, heal_amount))

        return events

    def _gain_mana(self, hero: Hero, amount: int, reason: str = "") -> list[Event]:
        if not hero.alive:
            return []
        actual = min(amount, self.MAX_MANA - hero.mana)
        if actual <= 0:
            return []
        hero.mana += actual
        return [Event(EventType.MANA_GAIN, {
            "slot": hero.slot, "amount": actual, "reason": reason,
        })]

    # ------------------------------------------------------------- madness

    def _pick_madness_action(self, hero: Hero) -> Action:
        pool: list[str] = ["__attack__"]
        if not is_silenced(hero):
            for aid in hero.template.ability_ids:
                ab = self.abilities[aid]
                if hero.mana < ab.mana_cost:
                    continue
                if self._ability_deals_damage(ab):
                    pool.append(aid)

        choice = self.rng.choice(pool)
        ally_side = self.rng.random() < 0.8

        def candidates(side: str) -> list[int]:
            if side == "ally":
                return [h.slot for h in self.heroes
                        if h.team == hero.team and h.alive and h.slot != hero.slot]
            return [h.slot for h in self.heroes if h.team != hero.team and h.alive]

        cands = candidates("ally" if ally_side else "enemy")
        if not cands:
            cands = candidates("enemy" if ally_side else "ally")
        if not cands:
            return Action(kind=ActionKind.MEDITATE, actor_slot=hero.slot)

        if choice == "__attack__":
            return Action(kind=ActionKind.ATTACK, actor_slot=hero.slot,
                          target_slots=(self.rng.choice(cands),))

        ability = self.abilities[choice]
        t = ability.targeting
        if t in (TargetingKind.SINGLE_ENEMY, TargetingKind.SINGLE_ALLY):
            return Action(kind=ActionKind.ABILITY, actor_slot=hero.slot,
                          ability_id=choice, target_slots=(self.rng.choice(cands),))
        if t == TargetingKind.ALL_ENEMIES:
            return Action(kind=ActionKind.ABILITY, actor_slot=hero.slot,
                          ability_id=choice, target_slots=tuple(cands))
        if t == TargetingKind.SELF:
            return Action(kind=ActionKind.ABILITY, actor_slot=hero.slot,
                          ability_id=choice, target_slots=(hero.slot,))
        return Action(kind=ActionKind.ABILITY, actor_slot=hero.slot,
                      ability_id=choice, target_slots=(self.rng.choice(cands),))

    def _ability_deals_damage(self, ability: AbilityTemplate) -> bool:
        if ability.damage_percent > 0:
            return True
        for ref in ability.effect_specs:
            cat = self.effects[ref.effect_id].category
            if cat in (EffectCategory.INSTANT_DAMAGE, EffectCategory.DOT):
                return True
        return False

    # ------------------------------------------------------------ snapshot

    def snapshot(self) -> BattleSnapshot:
        """Снимок состояния для view.

        Всегда ровно 10 HeroView — по одному на каждую координату слота 0..9.
        Пустые слоты (бой < 5×5) отдаются как placeholder:
        hero_id="", alive=False, hp=0.
        """
        hero_views: list[HeroView] = []
        for slot in range(10):
            hero = self._by_slot.get(slot)
            if hero is None:
                hero_views.append(HeroView(
                    slot=slot, hero_id="", name="",
                    team=0 if slot < 5 else 1,
                    hp=0, hp_max=0, mana=0, mana_max=self.MAX_MANA,
                    alive=False, effects=(),
                ))
            else:
                hero_views.append(self._hero_view(hero))

        active = self.current_actor()
        avail = self.available_actions(active) if active is not None else ()
        return BattleSnapshot(
            heroes=tuple(hero_views),
            active_slot=active,
            round_number=self.round_number,
            winner_team=self._winner,
            available_actions=tuple(avail),
        )

    def _hero_view(self, hero: Hero) -> HeroView:
        by_family: dict[str, list[Effect]] = {}
        for eff in hero.effects:
            by_family.setdefault(eff.family, []).append(eff)
        views: list[EffectView] = []
        for family, effs in by_family.items():
            spec = effs[0].spec
            views.append(EffectView(
                effect_id=spec.id, family=family, name=spec.name,
                category=spec.category.value,
                rounds_left=max(e.duration_left for e in effs),
                stacks=len(effs), description=spec.name,
                is_buff=self._is_buff(spec),
            ))
        return HeroView(
            slot=hero.slot, hero_id=hero.template.id, name=hero.template.name,
            team=hero.team, hp=hero.hp, hp_max=hero.template.hp,
            mana=hero.mana, mana_max=self.MAX_MANA,
            alive=hero.alive, effects=tuple(views),
        )

    def _is_buff(self, spec: EffectSpec) -> bool:
        return is_positive_effect(spec)


def battle_from_data(game_data: dict, settings: dict[str, Any],
                     top_ids: Iterable[str], bottom_ids: Iterable[str],
                     seed: int | None = None) -> Battle:
    idx = game_data["index"]
    top = [HeroTemplate.from_dict(idx["heroes"][h]) for h in top_ids]
    bottom = [HeroTemplate.from_dict(idx["heroes"][h]) for h in bottom_ids]
    abilities = {aid: AbilityTemplate.from_dict(d) for aid, d in idx["abilities"].items()}
    effects = {eid: EffectSpec.from_dict(d) for eid, d in idx["effects"].items()}
    return Battle(top, bottom, abilities, effects, set(idx["passives"].keys()),
                  settings, seed=seed)