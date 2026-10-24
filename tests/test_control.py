"""Тесты state machine и presenter. Без pygame."""
import pytest

from core.battle import battle_from_data
from core.contracts import ActionKind, PresentationCommandType
from core.events import Event, EventType
from control.battle_controller import BattleController, ControllerState
from control.presenter import event_to_commands, event_to_log_line


def make_battle(settings, game_data, seed=0):
    return battle_from_data(
        game_data, settings,
        top_ids=["handswing"], bottom_ids=["smut"], seed=seed,
    )


# -------------------------------------------------------------- presenter

def test_presenter_translates_attack():
    ev = Event(EventType.ATTACK,
               {"attacker": 0, "target": 5, "percent": 100.0})
    cmds = event_to_commands(ev)
    assert len(cmds) == 1
    assert cmds[0].type == PresentationCommandType.PLAY_ATTACK
    assert cmds[0].payload["target"] == 5


def test_presenter_translates_damage_crit():
    ev = Event(EventType.DAMAGE,
               {"source": 0, "target": 5, "amount": 220, "crit": True,
                "reflected": False})
    cmds = event_to_commands(ev)
    assert cmds[0].payload["kind"] == "crit"
    assert cmds[0].payload["value"] == 220


def test_presenter_translates_effect_and_death():
    applied = Event(EventType.EFFECT_APPLIED,
                    {"slot": 5, "effect_id": "burn_120_4r",
                     "family": "burn", "duration": 4})
    cmds = event_to_commands(applied)
    assert cmds[0].type == PresentationCommandType.PLAY_APPLY_EFFECT

    death = Event(EventType.DEATH, {"slot": 5})
    assert event_to_commands(death)[0].type == PresentationCommandType.PLAY_DEATH


def test_presenter_ignores_round_events():
    for et in (EventType.BATTLE_START, EventType.ROUND_START,
               EventType.ROUND_END):
        assert event_to_commands(Event(et, {})) == []


def test_log_line_formats():
    line = event_to_log_line(Event(EventType.DAMAGE,
                                   {"source": 0, "target": 1, "amount": 100,
                                    "crit": True, "reflected": False}))
    assert "КРИТ" in line and "-100" in line


# ----------------------------------------------------------- controller

def test_controller_waits_for_human(settings, game_data):
    battle = make_battle(settings, game_data)
    ctrl = BattleController(battle, ai_teams=set(), auto_skip_animations=True)
    ctrl.start()
    ctrl.update(0.016)
    assert ctrl.state in (ControllerState.WAIT_FOR_ACTION,
                          ControllerState.BATTLE_END)


def test_controller_meditation_flow(settings, game_data):
    battle = make_battle(settings, game_data)
    ctrl = BattleController(battle, ai_teams=set(), auto_skip_animations=True)
    ctrl.start()
    ctrl.update(0.016)
    if ctrl.state != ControllerState.WAIT_FOR_ACTION:
        pytest.skip("human hero didn't come first")
    actor_before = battle.current_actor()
    mana_before = battle.heroes[actor_before].mana

    assert ctrl.on_action_button(ActionKind.MEDITATE) is True
    ctrl.update(0.016)

    gained = battle.heroes[actor_before].mana - mana_before
    # В 1×1 после медитации сразу наступает конец раунда (+1 мана),
    # поэтому дельта — 2 (медитация) или 3 (медитация + конец раунда).
    assert gained in (2, 3)

    # В логе должна быть медитация, давшая ровно +2 маны.
    meditate_gains = [
        e for e in ctrl.log
        if e.type.value == "mana_gain"
        and e.payload.get("reason") == "meditate"
    ]
    assert any(e.payload["amount"] == 2 for e in meditate_gains)


def test_controller_attack_flow(settings, game_data):
    battle = make_battle(settings, game_data)
    ctrl = BattleController(battle, ai_teams=set(), auto_skip_animations=True)
    ctrl.start()
    ctrl.update(0.016)
    if ctrl.state != ControllerState.WAIT_FOR_ACTION:
        pytest.skip("human hero didn't come first")

    assert ctrl.on_action_button(ActionKind.ATTACK) is True
    assert ctrl.state == ControllerState.WAIT_FOR_TARGET
    valid = ctrl.valid_targets_for_current_action()
    assert len(valid) >= 1

    target = valid[0]
    assert ctrl.on_target_click(target) is True
    ctrl.update(0.016)
    # После атаки — либо новый ход, либо конец
    assert ctrl.state in (ControllerState.WAIT_FOR_ACTION,
                          ControllerState.WAIT_FOR_TARGET,
                          ControllerState.BATTLE_END)


def test_controller_rejects_invalid_target(settings, game_data):
    battle = make_battle(settings, game_data)
    ctrl = BattleController(battle, ai_teams=set(), auto_skip_animations=True)
    ctrl.start()
    ctrl.update(0.016)
    if ctrl.state != ControllerState.WAIT_FOR_ACTION:
        pytest.skip("human hero didn't come first")

    ctrl.on_action_button(ActionKind.ATTACK)
    valid = ctrl.valid_targets_for_current_action()
    invalid = next(s for s in range(10) if s not in valid)
    assert ctrl.on_target_click(invalid) is False
    assert ctrl.state == ControllerState.WAIT_FOR_TARGET  # не сдвинулись


def test_controller_cancel(settings, game_data):
    battle = make_battle(settings, game_data)
    ctrl = BattleController(battle, ai_teams=set(), auto_skip_animations=True)
    ctrl.start()
    ctrl.update(0.016)
    if ctrl.state != ControllerState.WAIT_FOR_ACTION:
        pytest.skip("human hero didn't come first")
    ctrl.on_action_button(ActionKind.ATTACK)
    assert ctrl.state == ControllerState.WAIT_FOR_TARGET
    ctrl.on_cancel()
    assert ctrl.state == ControllerState.WAIT_FOR_ACTION


def test_controller_ignores_action_in_wrong_state(settings, game_data):
    battle = make_battle(settings, game_data)
    ctrl = BattleController(battle, ai_teams=set(), auto_skip_animations=True)
    ctrl.start()  # состояние ANIMATING
    # Не вызываем update, чтобы остаться в ANIMATING
    assert ctrl.state == ControllerState.ANIMATING
    assert ctrl.on_action_button(ActionKind.ATTACK) is False


def test_controller_headless_finishes(settings, game_data):
    battle = battle_from_data(
        game_data, settings,
        top_ids=["handswing", "smut", "handswing"],
        bottom_ids=["smut", "handswing", "smut"],
        seed=7,
    )
    ctrl = BattleController(battle, ai_teams={0, 1}, auto_skip_animations=True)
    ctrl.start()
    steps = 0
    while ctrl.state != ControllerState.BATTLE_END and steps < 10000:
        ctrl.update(0.016)
        steps += 1
    assert ctrl.state == ControllerState.BATTLE_END
    assert battle.is_over()
    # Лог не пустой
    assert len(ctrl.log) > 0


# ---------------------------------------------------------- madness auto

def test_madness_does_not_require_user_input(settings, game_data):
    """Безумный герой не должен попасть в WAIT_FOR_ACTION."""
    battle = make_battle(settings, game_data)
    ctrl = BattleController(battle, ai_teams=set(), auto_skip_animations=True)
    ctrl.start()

    # Форсируем безумие на герое 0 ещё до его первого действия
    battle._apply_effect(battle.heroes[0], battle.effects["madness_2r"],
                         source_slot=5)

    ctrl.update(0.016)
    # MADNESS_ACTION должно появиться в логе (0-й герой сыграл хаотично)
    assert any(e.type == EventType.MADNESS_ACTION for e in ctrl.log)