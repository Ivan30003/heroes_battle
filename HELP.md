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


## Анимации (M5)

### Поток
1. Controller в состоянии ANIMATING: queue = [cmd1..cmdN, REFRESH_SNAPSHOT].
2. BattleScreen._process_commands() дренирует queue целиком:
   каждая команда → create_animation() → AnimationManager.add().
3. Все анимации батча играются параллельно.
4. Пока AnimationManager.count() > 0, controller.update() не вызывается —
   state машина «ждёт», пока визуал не доиграет.
5. После опустошения — controller уже в WAIT_FOR_ACTION / AI_THINKING /
   BATTLE_END (переход случился в момент pop'а последнего REFRESH_SNAPSHOT).

### Правила
- Ввод блокируется, пока count() > 0 (SPACE — пропуск).
- Оверлей результата появляется только после count() == 0.
- auto_skip_animations=False в проде, True в тестах M1–M4.
- Анимации не мутируют состояние — только читают snapshot + payload события.

### Слои
- view/animation/** импортирует control.public_api (типы),
  view.theme, pygame. Core не импортирует.
- factory.create_animation(command, ...) → Animation | None.
  None = мгновенная команда (REFRESH_SNAPSHOT, SHOW_BATTLE_END).