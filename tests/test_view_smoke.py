"""Smoke-тесты view в headless-режиме. Не требуют реального окна."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest
import pygame

from control.battle_controller import BattleController, ControllerState
from control.screens import GameSession
from core.battle import battle_from_data
from view.assets import AssetManager
from view.screens.battle import BattleScreen
from view.theme import Theme


class _MockApp:
    def __init__(self, settings, game_data):
        self.settings = settings
        self.game_data = game_data
        self.width = settings["game"]["screen_width"]
        self.height = settings["game"]["screen_height"]
        self.assets = AssetManager(settings)
        self.theme = Theme(settings)
        self.session = GameSession(settings, game_data)
        self.restarted = 0
        self.menu_requested = 0

    def start_battle(self):
        self.restarted += 1

    def return_to_menu(self):
        self.menu_requested += 1


@pytest.fixture(scope="module", autouse=True)
def pygame_init():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def _make_screen(settings, game_data, seed: int = 0,
                 ai_teams={0, 1}) -> BattleScreen:
    battle = battle_from_data(
        game_data, settings,
        top_ids=["handswing"] * 5,
        bottom_ids=["smut"] * 5,
        seed=seed,
    )
    ctrl = BattleController(battle, ai_teams=ai_teams,
                            auto_skip_animations=True)
    ctrl.start()
    app = _MockApp(settings, game_data)
    return BattleScreen(app, ctrl)


def test_battle_screen_constructs_and_draws(settings, game_data):
    screen = _make_screen(settings, game_data)
    surface = pygame.Surface((settings["game"]["screen_width"],
                              settings["game"]["screen_height"]))
    screen.update(0.016)
    screen.draw(surface)
    assert screen.snapshot.active_slot is not None or screen.result_overlay


def test_battle_ai_vs_ai_reaches_result_overlay(settings, game_data):
    screen = _make_screen(settings, game_data, seed=3)
    surface = pygame.Surface((settings["game"]["screen_width"],
                              settings["game"]["screen_height"]))
    for _ in range(20000):
        screen.update(0.05)
        if screen.result_overlay is not None:
            break
    screen.draw(surface)
    assert screen.result_overlay is not None
    assert screen.controller.state == ControllerState.BATTLE_END


def test_battle_human_flow_attack(settings, game_data):
    screen = _make_screen(settings, game_data, seed=0, ai_teams=set())
    surface = pygame.Surface((settings["game"]["screen_width"],
                              settings["game"]["screen_height"]))
    for _ in range(200):
        screen.update(0.016)
        if screen.controller.state == ControllerState.WAIT_FOR_ACTION:
            break
    if screen.controller.state != ControllerState.WAIT_FOR_ACTION:
        pytest.skip("human hero did not come first")

    # Клик по кнопке «Атака»
    attack_btn = screen.action_panel.buttons[0][0]
    attack_btn.on_click()
    screen.update(0.016)
    assert screen.controller.state == ControllerState.WAIT_FOR_TARGET

    # Клик по валидной цели
    targets = screen.controller.valid_targets_for_current_action()
    assert targets
    screen._on_slot_click(targets[0])
    screen.update(0.016)
    screen.draw(surface)


def test_battle_human_cancel(settings, game_data):
    screen = _make_screen(settings, game_data, seed=0, ai_teams=set())
    for _ in range(200):
        screen.update(0.016)
        if screen.controller.state == ControllerState.WAIT_FOR_ACTION:
            break
    if screen.controller.state != ControllerState.WAIT_FOR_ACTION:
        pytest.skip("human hero did not come first")
    screen.action_panel.buttons[0][0].on_click()  # Атака
    screen.update(0.016)
    assert screen.controller.state == ControllerState.WAIT_FOR_TARGET
    screen._on_cancel_click()
    screen.update(0.016)
    assert screen.controller.state == ControllerState.WAIT_FOR_ACTION