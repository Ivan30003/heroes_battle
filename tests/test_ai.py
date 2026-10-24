"""Тесты AI. Без pygame."""
import pytest

from core.battle import battle_from_data
from core.contracts import ActionKind, TargetingKind
from ai.simple_ai import SimpleAI


def _battle(settings, game_data, seed=0, top=None, bottom=None):
    return battle_from_data(
        game_data, settings,
        top_ids=top or ["handswing"], bottom_ids=bottom or ["smut"],
        seed=seed,
    )


def test_ai_attacks_when_no_other_options(settings, game_data):
    battle = _battle(settings, game_data)
    # герой 0 (handswing) c 0 маны — доступны только ATTACK / MEDITATE
    action = SimpleAI().choose_action(battle, 0)
    assert action.kind == ActionKind.ATTACK
    assert action.target_slots and len(action.target_slots) == 1


def test_ai_prefers_kill(settings, game_data):
    battle = _battle(settings, game_data)
    hero = battle.heroes[0]
    enemy = battle.heroes[1]
    hero.mana = 10
    enemy.hp = 5
    action = SimpleAI().choose_action(battle, 0)
    assert action.kind == ActionKind.ABILITY
    assert action.ability_id == "deadly_throw"
    assert action.target_slots == (enemy.slot,)


def test_ai_heals_when_low(settings, game_data):
    battle = _battle(settings, game_data, top=["smut"], bottom=["handswing"])
    hero = battle.heroes[0]  # smut
    hero.hp = int(hero.template.hp * 0.2)
    hero.mana = 10
    action = SimpleAI().choose_action(battle, 0)
    assert action.kind == ActionKind.ABILITY
    assert action.ability_id == "drink"
    assert action.target_slots == (0,)  # лечит себя


def test_ai_uses_aoe_when_two_enemies(settings, game_data):
    battle = _battle(
        settings, game_data,
        top=["smut"], bottom=["handswing", "handswing"],
    )
    hero = battle.heroes[0]
    hero.mana = 10
    action = SimpleAI().choose_action(battle, 0)
    assert action.kind == ActionKind.ABILITY
    assert action.ability_id == "wine_sword"


def test_ai_meditates_if_nothing_useful(settings, game_data):
    """Атака всегда доступна — верим, что AI не вернёт MEDITATE без причины."""
    battle = _battle(settings, game_data)
    action = SimpleAI().choose_action(battle, 0)
    assert action.kind in (ActionKind.ATTACK, ActionKind.ABILITY)


@pytest.mark.parametrize("seed", range(5))
def test_ai_actions_always_valid(settings, game_data, seed):
    """Валидируем, что AI возвращает действия, которые battle примет."""
    battle = battle_from_data(
        game_data, settings,
        top_ids=["handswing", "smut", "handswing"],
        bottom_ids=["smut", "handswing", "smut"],
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
        action = ai.choose_action(battle, actor)
        assert action.actor_slot == actor
        battle.apply_action(action)
    assert battle.is_over()