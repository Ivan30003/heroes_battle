# Архитектура: зафиксированные контракты M0

## Слои и правило зависимостей
view → control → core. Обратных импортов нет.

## core (без pygame)
- Единственный источник истины.
- Публичный API Battle (M1):
  - apply_action(Action) -> list[Event]
  - advance_phase() -> list[Event]
  - snapshot() -> BattleSnapshot
  - available_actions(actor_slot) -> tuple[ActionKind, ...]
  - valid_targets(actor_slot, ability_id | None) -> tuple[int, ...]

## control (без pygame)
- Единственный посредник, знающий оба мира.
- Преобразует Event → PresentationCommand.
- Управляет state machine: WAIT_FOR_ACTION / WAIT_FOR_TARGET /
  AI_THINKING / RESOLVING / ANIMATING.
- Держит AnimationQueue: одна презентационная команда за раз (или группа).

## view (только pygame)
- Читает BattleSnapshot, получает PresentationCommand.
- Не мутирует state, не импортирует core.
- Владеет координатами слотов и таймингами анимаций.

## Автопроверки слоёв
tests/test_imports.py падает, если:
- в core/ встретится 'import pygame'
- в view/ встретится 'import core' напрямую