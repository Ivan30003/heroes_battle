"""Загрузка и валидация JSON. Никакого pygame."""
from __future__ import annotations

import json
import os
from typing import Any


def load_settings(path: str = "settings.json") -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_list(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path}: ожидался JSON-массив")
    return data


def _unique_ids(items: list[dict], kind: str) -> set[str]:
    ids: set[str] = set()
    for it in items:
        if "id" not in it:
            raise ValueError(f"{kind}: запись без поля 'id': {it}")
        if it["id"] in ids:
            raise ValueError(f"{kind}: дублирующийся id '{it['id']}'")
        ids.add(it["id"])
    return ids


def load_all(settings: dict[str, Any]) -> dict[str, Any]:
    base = settings["paths"]["data"]
    heroes = _load_list(os.path.join(base, "heroes.json"))
    abilities = _load_list(os.path.join(base, "abilities.json"))
    effects = _load_list(os.path.join(base, "effects.json"))
    passives = _load_list(os.path.join(base, "passives.json"))

    ability_ids = _unique_ids(abilities, "abilities")
    effect_ids = _unique_ids(effects, "effects")
    passive_ids = _unique_ids(passives, "passives")
    _unique_ids(heroes, "heroes")

    errors: list[str] = []

    for h in heroes:
        for aid in h.get("ability_ids", []):
            if aid not in ability_ids:
                errors.append(f"hero '{h['id']}': неизвестная способность '{aid}'")
        for pid in h.get("passive_ids", []):
            if pid not in passive_ids:
                errors.append(f"hero '{h['id']}': неизвестная пассивка '{pid}'")

    for a in abilities:
        for spec in a.get("effect_specs", []):
            if spec.get("effect_id") not in effect_ids:
                errors.append(
                    f"ability '{a['id']}': неизвестный эффект '{spec.get('effect_id')}'"
                )

    for e in effects:
        for key in ("family", "category", "duration_type", "duration",
                    "dispellable", "stackable", "payload"):
            if key not in e:
                errors.append(f"effect '{e.get('id')}': отсутствует поле '{key}'")

    if errors:
        raise ValueError("Ошибки в данных:\n  - " + "\n  - ".join(errors))

    return {
        "heroes": heroes,
        "abilities": abilities,
        "effects": effects,
        "passives": passives,
        "index": {
            "heroes": {h["id"]: h for h in heroes},
            "abilities": {a["id"]: a for a in abilities},
            "effects": {e["id"]: e for e in effects},
            "passives": {p["id"]: p for p in passives},
        },
    }