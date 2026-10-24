"""Состояние игровой сессии: кто чем управляет, кто где сражается.

Экранная отрисовка живёт во view; этот модуль — только данные.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Screen(str, Enum):
    MENU = "menu"
    PREPARATION = "preparation"
    BATTLE = "battle"
    RESULT = "result"


@dataclass
class TeamConfig:
    hero_ids: list[str] = field(default_factory=list)
    ai: bool = False


class GameSession:
    def __init__(self, settings: dict[str, Any], game_data: dict[str, Any]):
        self.settings = settings
        self.game_data = game_data
        self.screen: Screen = Screen.MENU
        self.top = TeamConfig()
        self.bottom = TeamConfig()
        self.seed: int | None = None
        self._battle = None
        self._controller = None

    def start_battle(self):
        # импорт здесь, чтобы не тянуть core в слой screens на этапе загрузки
        from core.battle import battle_from_data
        from control.battle_controller import BattleController

        self._battle = battle_from_data(
            self.game_data, self.settings,
            top_ids=self.top.hero_ids,
            bottom_ids=self.bottom.hero_ids,
            seed=self.seed,
        )
        ai_teams = set()
        if self.top.ai:
            ai_teams.add(0)
        if self.bottom.ai:
            ai_teams.add(1)
        self._controller = BattleController(self._battle, ai_teams=ai_teams)
        self._controller.start()
        self.screen = Screen.BATTLE
        return self._controller

    @property
    def controller(self):
        return self._controller

    @property
    def battle(self):
        return self._battle