"""Единственная точка, через которую view получает типы core.

Правило архитектуры: view не должен импортировать core напрямую.
Всё, что нужно UI из контрактов ядра, реэкспортируется здесь.

view делает:
    from control.public_api import ActionKind, EventType, ControllerState
"""
from __future__ import annotations

# --- контракты (core/contracts.py) -----------------------------------------
from core.contracts import (
    Action,
    ActionKind,
    BattleSnapshot,
    EffectView,
    HeroView,
    PresentationCommand,
    PresentationCommandType,
    TargetingKind,
)

# --- события (core/events.py) ----------------------------------------------
from core.events import Event, EventType

# --- control's own state ---------------------------------------------------
from control.battle_controller import ControllerState

__all__ = [
    "Action", "ActionKind", "BattleSnapshot", "EffectView", "HeroView",
    "PresentationCommand", "PresentationCommandType", "TargetingKind",
    "Event", "EventType",
    "ControllerState",
]