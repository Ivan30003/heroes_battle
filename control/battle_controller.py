"""State machine боя. Единственный посредник между core и view/AI."""
from __future__ import annotations

from collections import deque
from enum import Enum
from typing import Optional

from core.battle import Battle
from core.contracts import (
    Action, ActionKind, BattleSnapshot, PresentationCommand, TargetingKind,
)
from core.events import Event
from core.stats import is_mad

from control.presenter import events_to_commands, event_to_log_line
from ai.simple_ai import SimpleAI


class ControllerState(str, Enum):
    IDLE = "idle"
    WAIT_FOR_ACTION = "wait_for_action"
    WAIT_FOR_TARGET = "wait_for_target"
    AI_THINKING = "ai_thinking"
    RESOLVING = "resolving"
    ANIMATING = "animating"
    BATTLE_END = "battle_end"


class BattleController:
    """Управляет ходом боя, чередуя ввод, AI и анимации."""

    MAX_STEPS_PER_UPDATE = 5000

    def __init__(
        self,
        battle: Battle,
        ai_teams: set[int] | None = None,
        auto_skip_animations: bool = False,
        ai: SimpleAI | None = None,
        ai_think_delay: float = 0.0,
    ):
        self.battle = battle
        self.ai_teams = set(ai_teams or ())
        self.auto_skip = auto_skip_animations
        self.ai = ai or SimpleAI()
        self.ai_think_delay = ai_think_delay
        self._ai_think_timer = 0.0

        self.state = ControllerState.IDLE
        self.command_queue: deque[PresentationCommand] = deque()
        self.log: list[Event] = []
        self.log_lines: list[str] = []
        self.pending_ability_id: str | None = None

    # ------------------------------------------------------------- lifecycle

    def start(self) -> None:
        events = self.battle.start()
        self._process_events(events)
        self.state = (ControllerState.ANIMATING
                      if self.command_queue else ControllerState.IDLE)
        if not self.command_queue:
            self._advance()

    def update(self, dt: float = 0.016) -> None:
        """Продвинуть state machine. Вызывается каждый кадр из view."""
        if self._ai_think_timer > 0:
            self._ai_think_timer = max(0.0, self._ai_think_timer - dt)

        for _ in range(self.MAX_STEPS_PER_UPDATE):
            if self.state in (ControllerState.IDLE,
                              ControllerState.WAIT_FOR_ACTION,
                              ControllerState.WAIT_FOR_TARGET,
                              ControllerState.BATTLE_END):
                return

            if self.state == ControllerState.AI_THINKING:
                if self._ai_think_timer > 0 and not self.auto_skip:
                    return
                self._run_ai()
                continue

            if self.state == ControllerState.ANIMATING:
                if self.auto_skip:
                    self.command_queue.clear()
                    self._advance()
                    continue
                return

            if self.state == ControllerState.RESOLVING:
                self._advance()
                continue

            raise RuntimeError(f"Unexpected state {self.state}")

        raise RuntimeError("State machine did not settle")

    # ---------------------------------------------------------- human input

    def on_action_button(self, kind: ActionKind,
                         ability_id: str | None = None) -> bool:
        if self.state != ControllerState.WAIT_FOR_ACTION:
            return False
        actor = self.battle.current_actor()
        if actor is None:
            return False

        if kind not in self.battle.available_actions(actor):
            return False

        if kind == ActionKind.MEDITATE:
            self._submit_action(Action(ActionKind.MEDITATE, actor))
            return True

        if kind == ActionKind.ATTACK:
            self.pending_ability_id = None
            self.state = ControllerState.WAIT_FOR_TARGET
            return True

        if kind == ActionKind.ABILITY:
            if ability_id is None:
                return False
            if ability_id not in self.battle.available_abilities(actor):
                return False
            ability = self.battle.abilities[ability_id]
            if ability.targeting in (TargetingKind.SINGLE_ENEMY,
                                     TargetingKind.SINGLE_ALLY):
                self.pending_ability_id = ability_id
                self.state = ControllerState.WAIT_FOR_TARGET
                return True
            self._submit_action(Action(ActionKind.ABILITY, actor,
                                       ability_id=ability_id))
            return True

        return False

    def on_target_click(self, slot: int) -> bool:
        if self.state != ControllerState.WAIT_FOR_TARGET:
            return False
        actor = self.battle.current_actor()
        if actor is None:
            return False

        if self.pending_ability_id is None:
            valid = self.battle.valid_targets(actor)
            action = Action(ActionKind.ATTACK, actor, target_slots=(slot,))
        else:
            valid = self.battle.valid_targets(actor, self.pending_ability_id)
            action = Action(ActionKind.ABILITY, actor,
                            ability_id=self.pending_ability_id,
                            target_slots=(slot,))

        if slot not in valid:
            return False

        self.pending_ability_id = None
        self._submit_action(action)
        return True

    def on_cancel(self) -> None:
        if self.state == ControllerState.WAIT_FOR_TARGET:
            self.pending_ability_id = None
            self.state = ControllerState.WAIT_FOR_ACTION

    def valid_targets_for_current_action(self) -> tuple[int, ...]:
        if self.state != ControllerState.WAIT_FOR_TARGET:
            return ()
        actor = self.battle.current_actor()
        if actor is None:
            return ()
        if self.pending_ability_id is None:
            return self.battle.valid_targets(actor)
        return self.battle.valid_targets(actor, self.pending_ability_id)

    # --------------------------------------------------------- view polling

    def poll_command(self) -> PresentationCommand | None:
        if self.state != ControllerState.ANIMATING or not self.command_queue:
            return None
        return self.command_queue[0]

    def on_command_finished(self) -> None:
        if self.state != ControllerState.ANIMATING:
            return
        if self.command_queue:
            self.command_queue.popleft()
        if not self.command_queue:
            self._advance()

    def skip_current_animation(self) -> None:
        if self.state != ControllerState.ANIMATING:
            return
        self.command_queue.clear()
        self._advance()

    # -------------------------------------------------------------- queries

    def snapshot(self) -> BattleSnapshot:
        return self.battle.snapshot()

    # ------------------------------------------------------------- internal

    def _advance(self) -> None:
        if self.battle.is_over():
            self.state = ControllerState.BATTLE_END
            return
        actor = self.battle.current_actor()
        if actor is None:
            self.state = ControllerState.BATTLE_END
            return

        hero = self.battle.hero_at(actor)   # ← было self.battle.heroes[actor]
        if is_mad(hero):
            self._submit_action(Action(ActionKind.MEDITATE, actor))
            return
        if hero.team in self.ai_teams:
            self.state = ControllerState.AI_THINKING
            self._ai_think_timer = self.ai_think_delay
            return
        self.state = ControllerState.WAIT_FOR_ACTION

    def _run_ai(self) -> None:
        actor = self.battle.current_actor()
        if actor is None:
            self.state = ControllerState.BATTLE_END
            return
        action = self.ai.choose_action(self.battle, actor)
        if action is None:
            action = Action(ActionKind.MEDITATE, actor)
        self._submit_action(action)

    def _submit_action(self, action: Action) -> None:
        self.state = ControllerState.RESOLVING
        events = self.battle.apply_action(action)
        self._process_events(events)
        self.state = (ControllerState.ANIMATING
                      if self.command_queue else ControllerState.RESOLVING)
        if not self.command_queue:
            self._advance()

    def _process_events(self, events: list[Event]) -> None:
        self.log.extend(events)
        for ev in events:
            line = event_to_log_line(ev)
            if line:
                self.log_lines.append(line)
        self.command_queue.extend(events_to_commands(events))