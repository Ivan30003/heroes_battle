"""Тесты чистой логики M1."""
import pytest

from core.battle import Battle, battle_from_data
from core.contracts import Action, ActionKind
from core.effect import EffectSpec
from core.hero import Hero, HeroTemplate


def force_actor(battle, slot: int) -> None:
    """Форсировать конкретного актора в обход Battle.start().

    Зачем: Battle.start() перемешивает порядок через rng.shuffle,
    и в 1×1 "первым ходит a или b" зависит от seed и версии Python.
    В тестах, где нужно, чтобы атаковал именно `a` (slot=0),
    мы просто выставляем очередь вручную.
    """
    if battle.round_number == 0:
        battle.round_number = 1
    battle.current_order = [slot]
    battle.current_idx = 0


def _attack(battle, actor_slot: int, target_slot: int):
    return battle.apply_action(
        Action(ActionKind.ATTACK, actor_slot, target_slots=(target_slot,))
    )


def _pvp(settings, a, b, effects=None, seed=None):
    """Сокращение для боя 1×1: a (slot=0) vs b (slot=5)."""
    return make_battle(settings, [a], [b], effects=effects, seed=seed)


def make_hero(tid: str, attack: int = 100, defense: int = 100,
              hp: int = 1000, dodge: float = 0.0, crit: float = 0.0,
              abilities=(), passives=()) -> HeroTemplate:
    return HeroTemplate(
        id=tid, name=tid, sprite_path="x.png",
        hp=hp, attack=attack, defense=defense,
        dodge=dodge, crit=crit,
        ability_ids=tuple(abilities),
        passive_ids=tuple(passives),
    )


def make_battle(settings, top, bottom, abilities=None, effects=None,
                passives=None, seed=0) -> Battle:
    return Battle(
        top_heroes=list(top),
        bottom_heroes=list(bottom),
        abilities=abilities or {},
        effects=effects or {},
        passives=set(passives or []),
        settings=settings,
        seed=seed,
    )


# ------------------------------------------------------------------ формула

def test_damage_basic_formula(settings):
    a = make_hero("a", attack=100, defense=100)
    b = make_hero("b", attack=100, defense=100, hp=1000)
    battle = _pvp(settings, a, b)
    force_actor(battle, slot=0)
    _attack(battle, 0, 5)                       # a(slot=0) → b(slot=5)
    assert battle.hero_at(5).hp == 900


def test_damage_defense_reduces(settings):
    a = make_hero("a", attack=100)
    b = make_hero("b", defense=200, hp=1000)
    battle = _pvp(settings, a, b)
    force_actor(battle, slot=0)
    _attack(battle, 0, 5)
    assert battle.hero_at(5).hp == 950


def test_defense_floor(settings, game_data):
    """Дебафф не опускает защиту ниже 30% от базовой."""
    from core.hero import Hero as H
    effs = {e["id"]: EffectSpec.from_dict(e) for e in game_data["effects"]}
    a = make_hero("a", attack=1000, hp=10000)
    b = make_hero("b", defense=100, hp=10000)
    battle = make_battle(settings, [a], [b], effects=effs)
    battle.start()
    # Накладываем -200% защиты
    from core.effect import EffectSpec as ES
    bad_spec = ES(id="bad", family="def_down", name="x",
                  category=effs["atk_down_40_2r"].category,
                  duration_type=effs["atk_down_40_2r"].duration_type,
                  duration=1, dispellable=True, stackable=False,
                  payload={"stat": "defense", "mult": -2.0})
    battle._apply_effect(battle.heroes[1], bad_spec, source_slot=0)
    from core.stats import effective_stat
    # floor: defense = max(100*(1-2), 30) = 30
    assert effective_stat(battle.heroes[1], "defense") == pytest.approx(30.0)


# -------------------------------------------------------------- уклонение

def test_dodge_always_miss(settings):
    a = make_hero("a", attack=100)
    b = make_hero("b", dodge=1.0, hp=1000)
    battle = _pvp(settings, a, b)
    force_actor(battle, slot=0)
    events = _attack(battle, 0, 5)
    assert any(e.type.value == "miss" for e in events)
    assert battle.hero_at(5).hp == 1000


# ------------------------------------------------------ counter_on_miss

def test_counter_on_miss(settings):
    a = make_hero("a", attack=100, crit=0.0)
    b = make_hero("b", attack=100, defense=100, dodge=1.0, hp=1000,
                  passives=("counter_on_miss",))
    battle = _pvp(settings, a, b)
    force_actor(battle, slot=0)
    _attack(battle, 0, 5)
    assert battle.hero_at(0).hp == 1000 - 125
    assert battle.hero_at(5).hp == 1000


# -------------------------------------------------------------- отражение

def test_reflection_counter(settings, game_data):
    effs = {e["id"]: EffectSpec.from_dict(e) for e in game_data["effects"]}
    a = make_hero("a", attack=100, defense=100, hp=1000, crit=0.0)
    b = make_hero("b", attack=100, defense=100, hp=1000, dodge=0.0)
    battle = _pvp(settings, a, b, effects=effs)
    battle._apply_effect(battle.hero_at(5), effs["counter_80_4r"], source_slot=0)
    force_actor(battle, slot=0)
    _attack(battle, 0, 5)
    assert battle.hero_at(0).hp == 1000 - 80
    assert battle.hero_at(5).hp == 1000 - 100


# ---------------------------------------------------- замена / стаки эффектов

def test_unstackable_replaces_same_family(settings, game_data):
    effs = {e["id"]: EffectSpec.from_dict(e) for e in game_data["effects"]}
    a = make_hero("a")
    b = make_hero("b")
    battle = make_battle(settings, [a], [b], effects=effs, seed=5)
    # Два разных ожога одного семейства
    from core.effect import EffectSpec as ES
    burn_short = ES(id="burn_s", family="burn", name="ожог",
                    category=effs["burn_120_4r"].category,
                    duration_type=effs["burn_120_4r"].duration_type,
                    duration=2, dispellable=True, stackable=False,
                    payload={"damage": 160})
    battle._apply_effect(battle.heroes[1], effs["burn_120_4r"], source_slot=0)
    assert len(battle.heroes[1].effects) == 1
    battle._apply_effect(battle.heroes[1], burn_short, source_slot=0)
    # Старый ожог заменён новым
    assert len(battle.heroes[1].effects) == 1
    assert battle.heroes[1].effects[0].spec.id == "burn_s"
    assert battle.heroes[1].effects[0].duration_left == 2


def test_different_families_coexist(settings, game_data):
    effs = {e["id"]: EffectSpec.from_dict(e) for e in game_data["effects"]}
    a = make_hero("a"); b = make_hero("b")
    battle = make_battle(settings, [a], [b], effects=effs, seed=5)
    battle._apply_effect(battle.heroes[1], effs["burn_120_4r"], source_slot=0)
    battle._apply_effect(battle.heroes[1], effs["poison_80_3r"], source_slot=0)
    assert len(battle.heroes[1].effects) == 2


# ----------------------------------------------------- duration семантика

def test_duration_two_rounds(settings, game_data):
    """duration=2, наложен в раунде 1 → активен в 1 и 2, исчезает в конце 2."""
    effs = {e["id"]: EffectSpec.from_dict(e) for e in game_data["effects"]}
    a = make_hero("a"); b = make_hero("b")
    battle = make_battle(settings, [a], [b], effects=effs, seed=6)
    battle.start()
    assert battle.round_number == 1
    battle._apply_effect(battle.heroes[1], effs["atk_down_40_2r"], source_slot=0)
    assert len(battle.heroes[1].effects) == 1
    # Завершаем раунд 1
    battle._resolve_round_end()
    assert len(battle.heroes[1].effects) == 1
    # Завершаем раунд 2
    battle._resolve_round_end()
    assert len(battle.heroes[1].effects) == 0


# ---------------------------------------------- стан +40% аддитивно

def test_stun_damage_taken_mult(settings, game_data):
    effs = {e["id"]: EffectSpec.from_dict(e) for e in game_data["effects"]}
    a = make_hero("a", attack=100, defense=100, crit=0.0, hp=10000)
    b = make_hero("b", defense=100, hp=10000)
    battle = _pvp(settings, a, b, effects=effs)
    battle._apply_effect(battle.hero_at(5), effs["stun_2r"], source_slot=0)
    force_actor(battle, slot=0)
    _attack(battle, 0, 5)
    assert battle.hero_at(5).hp == 10000 - 140


# -------------------------------------------------- mana cap + старт

def test_mana_cap_and_start(settings, game_data):
    a = make_hero("a", passives=("start_mana_1",))
    b = make_hero("b")
    battle = make_battle(settings, [a], [b], seed=8)
    assert battle.heroes[0].mana == 1
    # Заполним ману до 9 и нажмём медитацию
    battle.start()
    battle.heroes[0].mana = 9
    actor = battle.current_actor()
    battle.apply_action(Action(ActionKind.MEDITATE, actor))
    assert battle.heroes[0].mana == 10  # cap


# ----------------------------------------------------- mana_font passive

def test_mana_font(settings, game_data):
    effs = {e["id"]: EffectSpec.from_dict(e) for e in game_data["effects"]}
    font = make_hero("smut", attack=84, passives=("mana_font",))
    ally = make_hero("ally", attack=200)
    enemy = make_hero("enemy", attack=100, hp=10000)
    battle = make_battle(settings, [font, ally], [enemy], effects=effs, seed=9)
    battle.start()
    # эмулируем конец раунда: ally должен получить +1 (от mana_font) и +1 (round_end)
    battle._resolve_round_end()
    assert battle.heroes[1].mana == 2


# ---------------------------------------------------------- смерть и эффекты

def test_death_clears_effects(settings, game_data):
    effs = {e["id"]: EffectSpec.from_dict(e) for e in game_data["effects"]}
    a = make_hero("a", attack=100, hp=1, defense=100, crit=0.0)
    b = make_hero("b", hp=1000)
    battle = make_battle(settings, [a], [b], effects=effs, seed=10)
    battle.start()
    battle._apply_effect(battle.heroes[0], effs["burn_120_4r"], source_slot=1)
    assert len(battle.heroes[0].effects) == 1
    # a умирает от DOT
    battle._resolve_round_end()
    assert not battle.heroes[0].alive
    assert battle.heroes[0].effects == []


# --------------------------------------------------------------- ничья

def test_draw_simultaneous_dot(settings, game_data):
    effs = {e["id"]: EffectSpec.from_dict(e) for e in game_data["effects"]}
    a = make_hero("a", hp=100)
    b = make_hero("b", hp=100)
    battle = make_battle(settings, [a], [b], effects=effs, seed=11)
    battle.start()
    from core.effect import EffectSpec as ES
    burn = ES(id="burn", family="burn", name="ожог",
              category=effs["burn_120_4r"].category,
              duration_type=effs["burn_120_4r"].duration_type,
              duration=4, dispellable=True, stackable=False,
              payload={"damage": 120})
    battle._apply_effect(battle.hero_at(0), burn, source_slot=5)
    battle._apply_effect(battle.hero_at(5), burn, source_slot=0)
    battle._resolve_round_end()
    assert battle.is_over()
    assert battle.winner() is None


# -------------------------------------------------------------- безумие

def test_madness_never_targets_self(settings, game_data):
    idx = game_data["index"]
    hs = [idx["heroes"][hid] for hid in ("handswing", "smut")]
    effs = {e["id"]: EffectSpec.from_dict(e) for e in game_data["effects"]}
    abils = {a["id"]: __import__("core.ability", fromlist=["AbilityTemplate"])
             .AbilityTemplate.from_dict(a) for a in game_data["abilities"]}
    from core.hero import HeroTemplate as HT
    top = [HT.from_dict(h) for h in [hs[0], hs[1]]]
    bottom = [HT.from_dict(h) for h in [hs[0], hs[1]]]
    for seed in range(30):
        battle = Battle(top, bottom, abils, effs, set(idx["passives"].keys()),
                        settings, seed=seed)
        battle.start()
        hero = battle.heroes[0]
        battle._apply_effect(hero, effs["madness_2r"], source_slot=5)
        action = battle._pick_madness_action(hero)
        assert hero.slot not in action.target_slots


def test_madness_never_meditate(settings, game_data):
    idx = game_data["index"]
    effs = {e["id"]: EffectSpec.from_dict(e) for e in game_data["effects"]}
    from core.ability import AbilityTemplate
    abils = {a["id"]: AbilityTemplate.from_dict(a) for a in game_data["abilities"]}
    from core.hero import HeroTemplate as HT
    top = [HT.from_dict(idx["heroes"]["handswing"]), HT.from_dict(idx["heroes"]["smut"])]
    bottom = [HT.from_dict(idx["heroes"]["handswing"]), HT.from_dict(idx["heroes"]["smut"])]
    for seed in range(30):
        battle = Battle(top, bottom, abils, effs, set(idx["passives"].keys()),
                        settings, seed=seed)
        battle.start()
        hero = battle.heroes[0]
        battle._apply_effect(hero, effs["madness_2r"], source_slot=5)
        action = battle._pick_madness_action(hero)
        assert action.kind != ActionKind.MEDITATE


# ----------------------------------------------------- полный прогон боёв

def _random_bot(battle, actor_slot):
    """Простейший бот: случайное доступное действие, случайная цель."""
    import random
    rng = random.Random(hash((battle.round_number, actor_slot)))
    actions = battle.available_actions(actor_slot)
    if not actions:
        return None
    kind = rng.choice(actions)
    if kind == ActionKind.MEDITATE:
        return Action(kind, actor_slot)
    if kind == ActionKind.ATTACK:
        targets = battle.valid_targets(actor_slot)
        return Action(kind, actor_slot, target_slots=(rng.choice(targets),))
    abilities = battle.available_abilities(actor_slot)
    aid = rng.choice(abilities)
    ab = battle.abilities[aid]
    tgt = battle.valid_targets(actor_slot, aid)
    if not tgt:
        return Action(kind, actor_slot, ability_id=aid)
    return Action(kind, actor_slot, ability_id=aid, target_slots=(rng.choice(tgt),))


@pytest.mark.parametrize("seed", range(10))
def test_full_battle_terminates(settings, game_data, seed):
    """AI vs AI — бой всегда завершается, без исключений, без нарушения cap/floor."""
    battle = battle_from_data(
        game_data, settings,
        top_ids=["handswing", "smut", "handswing", "smut", "handswing"],
        bottom_ids=["smut", "handswing", "smut", "handswing", "smut"],
        seed=seed,
    )
    events = battle.start()
    safety = 0
    while not battle.is_over():
        safety += 1
        assert safety < 5000, "Бой не завершился за 5000 итераций"
        actor = battle.current_actor()
        assert actor is not None
        action = _random_bot(battle, actor)
        if action is None:
            # Теоретически не бывает: если действий нет — значит, стан,
            # но тогда мы бы не оказались в current_actor
            break
        events.extend(battle.apply_action(action))
        # Проверка инвариантов
        for h in battle.heroes:
            assert 0 <= h.mana <= battle.MAX_MANA
            assert h.hp <= h.template.hp
    assert battle.is_over()
    winner = battle.winner()
    assert winner in (0, 1, None)
    # Есть событие завершения боя
    assert any(e.type.value == "battle_end" for e in events)


def test_snapshot_pads_to_10(settings, game_data):
    """snapshot() всегда отдаёт 10 HeroView, пустые слоты — placeholder."""
    battle = battle_from_data(
        game_data, settings,
        top_ids=["handswing"], bottom_ids=["smut"], seed=0,
    )
    battle.start()
    snap = battle.snapshot()
    assert len(snap.heroes) == 10
    assert snap.heroes[0].slot == 0
    assert snap.heroes[0].hero_id == "handswing"
    assert snap.heroes[5].slot == 5
    assert snap.heroes[5].hero_id == "smut"
    for s in (1, 2, 3, 4, 6, 7, 8, 9):
        assert snap.heroes[s].slot == s
        assert snap.heroes[s].hero_id == ""
        assert not snap.heroes[s].alive
        assert snap.heroes[s].hp == 0


def test_snapshot_full_team_has_no_placeholders(settings, game_data):
    battle = battle_from_data(
        game_data, settings,
        top_ids=["handswing"] * 5, bottom_ids=["smut"] * 5, seed=0,
    )
    battle.start()
    snap = battle.snapshot()
    assert len(snap.heroes) == 10
    assert all(h.hero_id for h in snap.heroes)