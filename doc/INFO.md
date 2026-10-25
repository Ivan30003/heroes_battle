## Публичное API control для view

view импортирует типы из core **только** через control.public_api:

    from control.public_api import (
        Action, ActionKind, BattleSnapshot, EffectView, HeroView,
        PresentationCommand, PresentationCommandType, TargetingKind,
        Event, EventType, ControllerState,
    )

Прямой импорт `from core...` в view/ запрещён и проверяется
тестом tests/test_imports.py::test_view_does_not_import_core.