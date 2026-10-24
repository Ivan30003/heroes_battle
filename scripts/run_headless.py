"""Бой AI vs AI без графики. Проверка работы M2 и удобный лог."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.loader import load_all, load_settings
from core.battle import battle_from_data
from control.battle_controller import BattleController, ControllerState


def main(seed: int = 42, verbose: bool = True) -> None:
    settings = load_settings("settings.json")
    data = load_all(settings)

    battle = battle_from_data(
        data, settings,
        top_ids=["handswing", "smut", "handswing", "smut", "handswing"],
        bottom_ids=["smut", "handswing", "smut", "handswing", "smut"],
        seed=seed,
    )
    ctrl = BattleController(battle, ai_teams={0, 1}, auto_skip_animations=True)
    ctrl.start()

    step = 0
    while ctrl.state != ControllerState.BATTLE_END:
        ctrl.update(0.016)
        step += 1
        if step > 20000:
            print("!! Safety limit reached — state machine is stuck")
            break

    print(f"Обновлений state machine: {step}")
    print(f"Раундов: {battle.round_number}")
    print(f"Событий в логе: {len(ctrl.log)}")
    w = battle.winner()
    print(f"Победитель: {'ничья' if w is None else ('верх' if w == 0 else 'низ')}")
    print("Финальное состояние:")
    for h in battle.heroes:
        status = "МЁРТВ" if not h.alive else f"HP {h.hp}/{h.template.hp}"
        side = "верх" if h.team == 0 else "низ"
        print(f"  [{h.slot}] {h.template.name:<12} ({side})  {status}  "
              f"mana {h.mana}")

    if verbose:
        print("\nПоследние 20 строк лога:")
        for line in ctrl.log_lines[-20:]:
            print("  " + line)


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    main(seed=seed)