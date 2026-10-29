"""Проверки механик Коммандора."""
import pytest

from core.battle import battle_from_data
from core.contracts import Action, ActionKind
from core.effect import EffectCategory
from core.hero import Hero, HeroTemplate


def _mk_hero(tid, attack=100, defense=100, hp=1000,
             abilities=(), passives=()) -> HeroTemplate:
    return HeroTemplate(
        id=tid, name=tid, sprite_path=f"{tid}.png",
        hp=hp, attack=attack, defense=defense,
        dodge=0.0, crit=0.0,
        ability_ids=tuple(abilities),
        passive_ids=tuple(passives),
    )


def _commander_battle(settings, game_data, top_ids, bottom_ids, seed=0):
    return battle_from_data(game_data, settings,
                            top_ids=top_ids, bottom_ids=bottom_ids, seed=seed)


def _force_actor(battle, slot):
    if battle.round_number == 0:
        battle.round_number = 1
    battle.current_order = [slot]
    battle.current_idx = 0


# --------------------------------------------------------------------- roster

def test_commander_present_in_roster(settings, game_data):
    assert "commander" in game_data["index"]["heroes"]
    h = game_data["index"]["heroes"]["commander"]
    assert h["hp"] == 855
    assert h["attack"] == 110
    assert h["defense"] == 112
    assert h["dodge"] == 0.0
    assert h["crit"] == 0.02
    assert set(h["ability_ids"]) == {"commander_rally", "commander_rally_crit"}
    assert set(h["passive_ids"]) == {
        "positive_effect_heal", "discipline", "command_aura"
    }


# ------------------------------------------------------------- ability 5 (aura)

def test_command_aura_grants_attack_to_all_allies(settings, game_data):
    """Все союзники Коммандора получают +10% атаки на старте боя."""
    battle = _commander_battle(
        settings, game_data,
        top_ids=["commander", "handswing", "smut"],
        bottom_ids=["tank", "paladin", "berserker"],
        seed=0,
    )
    from core.stats import effective_stat

    cmd = next(h for h in battle.heroes if h.template.id == "commander")
    hs = next(h for h in battle.heroes if h.template.id == "handswing")

    # до старта нет аур, после start() есть
    battle.start()

    # handswing: base 100 → 110 с аурой
    assert effective_stat(hs, "attack") == pytest.approx(110.0)
    # сам командор тоже получает +10%
    assert effective_stat(cmd, "attack") == pytest.approx(110 * 1.10)

    # у врагов ауры нет
    tank = next(h for h in battle.heroes if h.template.id == "tank")
    assert effective_stat(tank, "attack") == pytest.approx(75.0)


def test_command_aura_removed_on_commander_death(settings, game_data):
    """После смерти Коммандора аура снимается с союзников."""
    battle = _commander_battle(
        settings, game_data,
        top_ids=["commander", "handswing"],
        bottom_ids=["tank", "paladin"],
        seed=0,
    )
    from core.stats import effective_stat
    from core.contracts import Action, ActionKind

    battle.start()
    cmd = next(h for h in battle.heroes if h.template.id == "commander")
    hs = next(h for h in battle.heroes if h.template.id == "handswing")
    assert effective_stat(hs, "attack") == pytest.approx(110.0)

    # Убиваем командора - прямой установкой HP и вызовом _handle_death
    cmd.hp = 0
    battle._handle_death(cmd)

    assert effective_stat(hs, "attack") == pytest.approx(100.0)


# --------------------------------------------------------- ability 1 (rally)

def test_rally_buffs_all_allies(settings, game_data):
    """+45% атаки и +35% защиты всем живым союзникам на 3 раунда."""
    battle = _commander_battle(
        settings, game_data,
        top_ids=["commander", "handswing", "smut"],
        bottom_ids=["tank", "handswing", "smut"],
        seed=2,
    )
    battle.start()
    cmd = next(h for h in battle.heroes if h.template.id == "commander")
    hs = next(h for h in battle.heroes if h.template.id == "handswing")

    # Начисляем ману и форсируем ход
    cmd.mana = 10
    _force_actor(battle, cmd.slot)
    events = battle.apply_action(Action(ActionKind.ABILITY, cmd.slot,
                               ability_id="commander_rally"))
    print(f"\n{events=}\n")
    # Проверяем эффекты на handswing
    families = {e.family for e in hs.effects}
    assert "attack_up" in families
    assert "defense_up" in families

    # Оба эффекта длятся 3 раунда и тикнули 1 раз после окончания раунда. Осталось 2 раунда
    for e in hs.effects:
        if e.family in ("attack_up", "defense_up"):
            assert e.duration_left == 2


# --------------------------------------------------------- ability 2 (crit)

def test_rally_crit_neighbors_and_self_debuff(settings, game_data):
    """+35% крита соседям, -20% атаки себе."""
    battle = _commander_battle(
        settings, game_data,
        top_ids=["commander", "handswing", "smut"],   # commander slot_in_team=0
        bottom_ids=["tank"],
        seed=0,
    )
    battle.start()
    from core.stats import effective_stat

    cmd = next(h for h in battle.heroes if h.template.id == "commander")
    hs = next(h for h in battle.heroes if h.template.id == "handswing")
    smut = next(h for h in battle.heroes if h.template.id == "smut")

    cmd.mana = 10
    _force_actor(battle, cmd.slot)
    battle.apply_action(Action(ActionKind.ABILITY, cmd.slot,
                               ability_id="commander_rally_crit"))

    # Neighbor slot_in_team=1 → handswing должен получить crit
    assert any(e.family == "crit_up" for e in hs.effects)
    # Слот slot_in_team=2 (smut) — не сосед → нет crit_up
    assert not any(e.family == "crit_up" for e in smut.effects)
    # Сам командор получил -20% атаки
    assert any(e.family == "attack_down" for e in cmd.effects)
    # Effective attack командора = 109 * 1.10 (аура) * 0.80 (debuff) = 95.92
    assert effective_stat(cmd, "attack") == pytest.approx(110 * 1.10 * 0.80)


# ----------------------------------------------- passive 3 (positive heal)

def test_positive_effect_triggers_heal(settings, game_data):
    """Положительный эффект на Коммандора лечит его на 5% от макс. HP."""
    battle = _commander_battle(
        settings, game_data,
        top_ids=["commander"], bottom_ids=["handswing"],
        seed=0,
    )
    battle.start()
    cmd = next(h for h in battle.heroes if h.template.id == "commander")
    cmd.hp = 100  # искусственно низкое HP
    hp_before = cmd.hp

    # Применяем положительный эффект напрямую
    from core.effect import EffectSpec
    atk_up = EffectSpec.from_dict(
        next(e for e in game_data["effects"] if e["id"] == "atk_up_30_2r")
    )
    battle._apply_effect(cmd, atk_up, source_slot=cmd.slot)

    # 5% от 855 = 42
    assert cmd.hp == hp_before + 42


def test_debuff_does_not_trigger_heal(settings, game_data):
    """Отрицательный эффект на Коммандора НЕ лечит его."""
    battle = _commander_battle(
        settings, game_data,
        top_ids=["commander"], bottom_ids=["handswing"],
        seed=0,
    )
    battle.start()
    cmd = next(h for h in battle.heroes if h.template.id == "commander")
    cmd.hp = 200
    hp_before = cmd.hp

    from core.effect import EffectSpec
    atk_down = EffectSpec.from_dict(
        next(e for e in game_data["effects"] if e["id"] == "atk_down_40_2r")
    )
    battle._apply_effect(cmd, atk_down, source_slot=0)

    assert cmd.hp == hp_before


# ------------------------------------------ passive 4 (defense if idle)

def test_discipline_when_no_ability_used(settings, game_data):
    """После раунда без способности Коммандор получает +10% защиты."""
    battle = _commander_battle(
        settings, game_data,
        top_ids=["commander"], bottom_ids=["handswing"],
        seed=0,
    )
    battle.start()
    cmd = next(h for h in battle.heroes if h.template.id == "commander")

    # Форсируем "использовал обычную атаку в этом раунде"
    cmd.flags["used_ability_this_round"] = False

    # Завершаем раунд вручную
    battle._resolve_round_end()

    assert any(e.family == "defense_up_aura" for e in cmd.effects)


def test_discipline_not_triggered_if_ability_used(settings, game_data):
    """Если Коммандор использовал способность — бафф защиты не даётся."""
    battle = _commander_battle(
        settings, game_data,
        top_ids=["commander"], bottom_ids=["handswing"],
        seed=0,
    )
    battle.start()
    cmd = next(h for h in battle.heroes if h.template.id == "commander")

    cmd.flags["used_ability_this_round"] = True

    battle._resolve_round_end()

    assert not any(e.family == "defense_up_aura" for e in cmd.effects)


# ------------------------------------------------------- full integration

def test_commander_full_battle_no_crash(settings, game_data):
    """Полный бой с Коммандором в команде завершается без ошибок."""
    from ai.simple_ai import SimpleAI
    battle = _commander_battle(
        settings, game_data,
        top_ids=["commander", "handswing", "smut", "mage", "tank"],
        bottom_ids=["assassin", "archer", "necromancer", "berserker", "paladin"],
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
def test_commander_vs_commander_no_crash(settings, game_data, seed):
    """Два Коммандора с обеих сторон: ауры не ломают систему."""
    from ai.simple_ai import SimpleAI
    battle = _commander_battle(
        settings, game_data,
        top_ids=["commander", "handswing", "commander"],
        bottom_ids=["commander", "smut", "commander"],
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
