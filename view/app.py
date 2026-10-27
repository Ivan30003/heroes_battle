"""Точка сборки слоёв. Единственное место, где view инициализируется."""
from __future__ import annotations

from typing import Any

import pygame

from control.screens import GameSession, Screen
from view.assets import AssetManager
from view.screens.battle import BattleScreen
from view.screens.menu import MenuScreen
from view.screens.preparation import PreparationScreen
from view.theme import Theme


class App:
    def __init__(self, settings: dict[str, Any], game_data: dict[str, Any]):
        pygame.init()
        self.settings = settings
        self.game_data = game_data
        self.width = settings["game"]["screen_width"]
        self.height = settings["game"]["screen_height"]

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(settings["game"]["title"])
        self.clock = pygame.time.Clock()
        self.running = True

        self.assets = AssetManager(settings)
        self.theme = Theme(settings)
        self.session = GameSession(settings, game_data)

        self.current_screen = MenuScreen(self)

    # ---------------------------------------------------------- transitions

    def switch_screen(self, screen) -> None:
        self.current_screen = screen

    def start_preparation(self) -> None:
        self.session.screen = Screen.PREPARATION
        self.switch_screen(PreparationScreen(self))

    def start_battle(self) -> None:
        ctrl = self.session.start_battle(
            auto_skip_animations=False, ai_think_delay=0.4,
        )
        self.switch_screen(BattleScreen(self, ctrl))

    def return_to_menu(self) -> None:
        self.session.screen = Screen.MENU
        self.switch_screen(MenuScreen(self))

    def quit(self) -> None:
        self.running = False

    # ---------------------------------------------------------------- loop

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(self.settings["game"]["fps"]) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif (event.type == pygame.KEYDOWN
                      and event.key == pygame.K_ESCAPE
                      and isinstance(self.current_screen, MenuScreen)):
                    self.running = False
                else:
                    self.current_screen.handle_event(event)

            self.current_screen.update(dt)
            self.current_screen.draw(self.screen)
            pygame.display.flip()

        pygame.quit()