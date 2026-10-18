"""Точка входа. Валидирует JSON и запускает App."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.loader import load_all, load_settings
from view.app import App


def main() -> None:
    settings = load_settings("settings.json")
    game_data = load_all(settings)  # сразу падает с понятной ошибкой, если JSON битый
    print(
        f"[M0] settings.json загружен. "
        f"Данные: {len(game_data['heroes'])} героев, "
        f"{len(game_data['abilities'])} способностей, "
        f"{len(game_data['effects'])} эффектов, "
        f"{len(game_data['passives'])} пассивок."
    )
    App(settings, game_data).run()


if __name__ == "__main__":
    main()