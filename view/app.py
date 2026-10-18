"""Точка сборки слоёв. App — единственное место, где view инициализируется."""
from __future__ import annotations

from typing import Any

import pygame

from view.assets import AssetManager
from view.screens.menu import MenuScreen
from view.theme import Theme


class App:
    def __init__(self, settings: dict[str, Any], game_data: dict[str, Any]):
        pygame.init()
        self.settings = settings
        self.game_data = game_data
        self.screen = pygame.display.set_mode(
            (settings["game"]["screen_width"], settings["game"]["screen_height"])
        )
        pygame.display.set_caption(settings["game"]["title"])
        self.clock = pygame.time.Clock()
        self.running = True

        self.assets = AssetManager(settings)
        self.theme = Theme(settings)
        self.current_screen = MenuScreen(self)

    def switch_screen(self, screen) -> None:
        self.current_screen = screen

    def quit(self) -> None:
        self.running = False

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(self.settings["game"]["fps"]) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    self.current_screen.handle_event(event)

            self.current_screen.update(dt)
            self.current_screen.draw(self.screen)
            pygame.display.flip()

        pygame.quit()