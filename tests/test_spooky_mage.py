"""Тесты механик Жуткого мага (Spooky mage)."""
import pytest

from core.battle import battle_from_data
from core.contracts import Action, ActionKind
from core.effect import EffectCategory, EffectSpec


def _force_actor(battle, slot: int) -> None:
    if battle.round_number == 0:
        battle.round_number = 1
    battle.current_order = [slot]
    battle.current_idx = 0


def _spooky_battle(settings, game_data, top_ids, bottom_ids, seed=0):
    return battle_from_data(game_data, settings,
                            top_ids=top_ids, bottom_ids=bottom_ids, seed=seed)


# ---------------------------------------------------------------- roster

def test_spooky_mage_present_in_roster(settings, game_data):
    h = game_data["index"]["heroes"]["spooky_mage"]
    assert h["hp"] == 918
    assert h["attack"] == 126
    assert h["defense"] == 86
    assert h["dodge"] == 0.0
    assert h["crit"] == 0.01
    assert set(h["ability_ids"]) == {
        "ice_explosion", "acid_dart", "distortion_curse"
    }
    assert set(h["passive_ids"]) == {"jinx"}


# -------------------------------------------- SET-модификатор и floor

def test_defense_set_overrides_base(settings, game_data):
    from core.stats import effective_stat
    battle = _spooky_battle(settings, game_data,
                            top_ids=["spooky_mage"], bottom_ids=["tank"])
    battle.start()
    tank = next(h for h in battle.heroes if h.template.id == "tank")
    assert effective_stat(tank, "defense") == pytest.approx(140.0)

    spec = EffectSpec.from_dict(
        next(e for e in game_data["effects"]
             if e["id"] == "defense_set_70_2r"))
    battle._apply_effect(tank, spec, source_slot=0)
    assert effective_stat(tank, "defense") == pytest.approx(70.0)


def test_defense_set_respects_floor(settings, game_data):
    from core.stats import effective_stat
    battle = _spooky_battle(settings, game_data,
                            top_ids=["spooky_mage"], bottom_ids=["tank"])
    battle.start()
    tank = next(h for h in battle.heroes if h.template.id == "tank")
    spec = EffectSpec(
        id="test_set", family="defense_set", name="test",
        category=EffectCategory.STAT_MOD,
        duration_type="ROUNDS",
        duration=2, dispellable=True, stackable=False,
        payload={"stat": "defense", "set": 20},
    )
    battle._apply_effect(tank, spec, source_slot=0)
    # floor = 140 * 0.3 = 42
    assert effective_stat(tank, "defense") == pytest.approx(42.0)


def test_defense_set_classified_as_debuff(settings, game_data):
    """defense_set_70 не считается положительным эффектом (для jinx)."""
    from core.stats import is_positive_effect
    spec = EffectSpec.from_dict(
        next(e for e in game_data["effects"]
             if e["id"] == "defense_set_70_2r"))
    assert is_positive_effect(spec) is False


# ---------------------------------------------------------- acid dart

def test_acid_dart_damage_and_set_defense(settings, game_data):
    from core.stats import effective_stat
    battle = _spooky_battle(settings, game_data,
                            top_ids=["spooky_mage"], bottom_ids=["tank"])
    battle.start()
    sm = next(h for h in battle.heroes if h.template.id == "spooky_mage")
    tank = next(h for h in battle.heroes if h.template.id == "tank")

    sm.mana = 10
    _force_actor(battle, sm.slot)
    hp_before = tank.hp
    battle.apply_action(Action(ActionKind.ABILITY, sm.slot,
                               ability_id="acid_dart",
                               target_slots=(tank.slot,)))

    assert tank.hp < hp_before
    assert effective_stat(tank, "defense") == pytest.approx(70.0)


# ------------------------------------------------------- ice explosion

def test_ice_explosion_hits_all_and_debuffs(settings, game_data):
    battle = _spooky_battle(settings, game_data,
                            top_ids=["spooky_mage"],
                            bottom_ids=["tank", "handswing", "smut"])
    battle.start()
    sm = next(h for h in battle.heroes if h.template.id == "spooky_mage")
    enemies = [h for h in battle.heroes if h.team == 1]

    sm.mana = 10
    _force_actor(battle, sm.slot)
    hp_before = {h.slot: h.hp for h in enemies}
    battle.apply_action(Action(ActionKind.ABILITY, sm.slot,
                               ability_id="ice_explosion"))

    for e in enemies:
        assert e.hp < hp_before[e.slot]
        assert any(ef.family == "defense_down" for ef in e.effects)


# -------------------------------------------------- distortion curse

def test_distortion_curse_deals_exactly_150_and_silences(settings, game_data):
    battle = _spooky_battle(settings, game_data,
                            top_ids=["spooky_mage"], bottom_ids=["tank"])
    battle.start()
    sm = next(h for h in battle.heroes if h.template.id == "spooky_mage")
    tank = next(h for h in battle.heroes if h.template.id == "tank")

    sm.mana = 10
    _force_actor(battle, sm.slot)
    hp_before = tank.hp
    battle.apply_action(Action(ActionKind.ABILITY, sm.slot,
                               ability_id="distortion_curse",
                               target_slots=(tank.slot,)))

    # jinx: 0 положительных эффектов на танке → без бонуса
    assert tank.hp == hp_before - 150
    assert any(ef.family == "silence" for ef in tank.effects)


def test_distortion_curse_ignores_attack_boost(settings, game_data):
    """Бафф атаки самого мага не меняет фикс. урон 150."""
    battle = _spooky_battle(settings, game_data,
                            top_ids=["spooky_mage"], bottom_ids=["tank"])
    battle.start()
    sm = next(h for h in battle.heroes if h.template.id == "spooky_mage")
    tank = next(h for h in battle.heroes if h.template.id == "tank")

    atk_up = EffectSpec.from_dict(
        next(e for e in game_data["effects"] if e["id"] == "atk_up_30_2r"))
    battle._apply_effect(sm, atk_up, source_slot=sm.slot)

    sm.mana = 10
    _force_actor(battle, sm.slot)
    hp_before = tank.hp
    battle.apply_action(Action(ActionKind.ABILITY, sm.slot,
                               ability_id="distortion_curse",
                               target_slots=(tank.slot,)))
    assert tank.hp == hp_before - 150


def test_distortion_curse_responds_to_stun_bonus(settings, game_data):
    """Стан +40% входящего урона — единственный модификатор, действующий
    на фиксированный урон."""
    battle = _spooky_battle(settings, game_data,
                            top_ids=["spooky_mage"], bottom_ids=["tank"])
    battle.start()
    sm = next(h for h in battle.heroes if h.template.id == "spooky_mage")
    tank = next(h for h in battle.heroes if h.template.id == "tank")

    stun = EffectSpec.from_dict(
        next(e for e in game_data["effects"] if e["id"] == "stun_2r"))
    battle._apply_effect(tank, stun, source_slot=0)

    sm.mana = 10
    _force_actor(battle, sm.slot)
    hp_before = tank.hp
    battle.apply_action(Action(ActionKind.ABILITY, sm.slot,
                               ability_id="distortion_curse",
                               target_slots=(tank.slot,)))
    # 150 * 1.4 = 210
    assert tank.hp == hp_before - 210


# ----------------------------------------------------------------- jinx

def _damage_from_attack(settings, game_data, extra_effects=()):
    """Возвращает урон обычной атаки мага по танку с заданными эффектами."""
    battle = _spooky_battle(settings, game_data,
                            top_ids=["spooky_mage"], bottom_ids=["tank"])
    battle.start()
    sm = next(h for h in battle.heroes if h.template.id == "spooky_mage")
    tank = next(h for h in battle.heroes if h.template.id == "tank")

    for eff_id in extra_effects:
        spec = EffectSpec.from_dict(
            next(e for e in game_data["effects"] if e["id"] == eff_id))
        battle._apply_effect(tank, spec, source_slot=0)

    hp_before = tank.hp
    _force_actor(battle, sm.slot)
    battle.apply_action(Action(ActionKind.ATTACK, sm.slot,
                               target_slots=(tank.slot,)))
    return hp_before - tank.hp


def test_jinx_boosts_per_positive_effect(settings, game_data):
    """+5% урона за каждый положительный эффект на цели."""
    baseline = _damage_from_attack(settings, game_data)
    with_one = _damage_from_attack(settings, game_data,
                                   extra_effects=("atk_up_30_2r",))
    with_two = _damage_from_attack(settings, game_data,
                                   extra_effects=("atk_up_30_2r",
                                                  "defense_up_2_2r"))
    # 100 * 126/140 = 90 базовый урон
    assert baseline == pytest.approx(90, abs=2)
    assert with_one == pytest.approx(round(baseline * 1.05), abs=2)
    assert with_two == pytest.approx(round(baseline * 1.10 / 1.02), abs=2)
    # Монотонный рост
    assert baseline < with_one < with_two


def test_jinx_ignores_debuffs(settings, game_data):
    """Дебаффы на цели не считаются."""
    debuff = _damage_from_attack(settings, game_data,
                                 extra_effects=("atk_down_40_2r",))
    baseline = _damage_from_attack(settings, game_data)
    assert debuff == baseline


def test_jinx_ignores_dot_and_control(settings, game_data):
    """DOT и контроль не дают бонуса."""
    poison = _damage_from_attack(settings, game_data,
                                 extra_effects=("poison_80_3r",))
    silence = _damage_from_attack(settings, game_data,
                                  extra_effects=("silence_2r",))
    baseline = _damage_from_attack(settings, game_data)
    POISON_DAMAGE = 80
    assert poison - POISON_DAMAGE == baseline
    assert silence == baseline


# ------------------------------------------------------- full battle

def test_spooky_mage_full_battle(settings, game_data):
    from ai.simple_ai import SimpleAI
    battle = _spooky_battle(
        settings, game_data,
        top_ids=["spooky_mage", "handswing", "smut", "mage", "tank"],
        bottom_ids=["healer", "assassin", "archer", "necromancer", "paladin"],
        seed=42,
    )
    ai = SimpleAI()
    battle.start()
    safety = 0
    while not battle.is_over() and safety < 5000:
        safety += 1
        actor = battle.current_actor()
        if actor is None:
            break
        battle.apply_action(ai.choose_action(battle, actor))
    assert battle.is_over()


@pytest.mark.parametrize("seed", range(5))
def test_spooky_mage_mirror_match(settings, game_data, seed):
    from ai.simple_ai import SimpleAI
    battle = _spooky_battle(
        settings, game_data,
        top_ids=["spooky_mage", "spooky_mage", "handswing"],
        bottom_ids=["spooky_mage", "spooky_mage", "handswing"],
        seed=seed,
    )
    ai = SimpleAI()
    battle.start()
    safety = 0
    while not battle.is_over() and safety < 5000:
        safety += 1
        actor = battle.current_actor()
        if actor is None:
            break
        battle.apply_action(ai.choose_action(battle, actor))
    assert battle.is_over()