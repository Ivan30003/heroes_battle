"""Опционально: сгенерировать PNG-плейсхолдеры в файловой системе.

Игра работает и без этого (AssetManager генерирует плейсхолдеры на лету),
но если хочется иметь PNG-файлы — запустите:

    python scripts/generate_placeholder_assets.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from data.loader import load_all, load_settings
from view.assets import AssetManager


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))

    settings = load_settings("settings.json")
    data = load_all(settings)
    assets = AssetManager(settings)

    os.makedirs(settings["paths"]["sprites"], exist_ok=True)
    os.makedirs(settings["paths"]["effect_icons"], exist_ok=True)
    os.makedirs(settings["paths"]["ability_icons"], exist_ok=True)
    os.makedirs(settings["paths"]["passive_icons"], exist_ok=True)

    # герои
    for h in data["heroes"]:
        path = os.path.join(settings["paths"]["sprites"],
                            os.path.basename(h["sprite_path"]))
        if not os.path.isfile(path):
            img = assets.hero_portrait(h["sprite_path"])
            pygame.image.save(img, path)
            print(f"  hero  {path}")

    # эффекты
    size = settings["ui"]["effect_icon_size"]
    for e in data["effects"]:
        path = os.path.join(settings["paths"]["effect_icons"],
                            f"{e['family']}.png")
        if not os.path.isfile(path):
            img = assets.effect_icon(e["family"])
            pygame.image.save(img, path)
            print(f"  fx    {path}")

    # способности
    for a in data["abilities"]:
        path = os.path.join(settings["paths"]["ability_icons"],
                            f"{a['id']}.png")
        if not os.path.isfile(path):
            img = assets.ability_icon(a["id"])
            pygame.image.save(img, path)
            print(f"  abil  {path}")

    # пассивки
    for p in data["passives"]:
        path = os.path.join(settings["paths"]["passive_icons"],
                            f"{p['id']}.png")
        if not os.path.isfile(path):
            img = assets.passive_icon(p["id"])
            pygame.image.save(img, path)
            print(f"  pasv  {path}")

    pygame.quit()
    print("Готово.")


if __name__ == "__main__":
    main()