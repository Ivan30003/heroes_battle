"""Проверки целостности контента M6."""
from data.loader import load_all, load_settings


def test_roster_has_at_least_10_heroes(settings):
    data = load_all(settings)
    assert len(data["heroes"]) >= 10, \
        f"Ожидалось ≥10 героев, получено {len(data['heroes'])}"


def test_all_heroes_reference_valid_content(settings):
    """Loader уже валидирует id; проверяем, что все герои имеют полный набор."""
    data = load_all(settings)
    for h in data["heroes"]:
        assert 1 <= len(h["ability_ids"]) <= 4, \
            f"{h['id']}: ожидалось 1..4 способности"
        assert 1 <= len(h["passive_ids"]) <= 3, \
            f"{h['id']}: ожидалось 1..3 пассивки"
        assert h["hp"] > 0 and h["attack"] > 0 and h["defense"] > 0
        assert 0.0 <= h["dodge"] <= 1.0
        assert 0.0 <= h["crit"] <= 1.0


def test_all_effects_have_family_and_payload(settings):
    data = load_all(settings)
    families = set()
    for e in data["effects"]:
        assert e["family"], f"{e['id']}: пустая family"
        assert e["payload"], f"{e['id']}: пустой payload"
        families.add(e["family"])
    # ключевые семейства на месте
    for expected in ("burn", "poison", "stun", "silence", "counter",
                     "attack_down", "attack_up", "defense_up",
                     "direct_damage", "heal_pct", "cleanse"):
        assert expected in families, f"Нет семейства {expected}"


def test_all_abilities_have_mana_and_targeting(settings):
    data = load_all(settings)
    valid_targetings = {"SELF", "SINGLE_ENEMY", "ALL_ENEMIES",
                        "SINGLE_ALLY", "ALL_ALLIES", "RANDOM_ADJACENT_ENEMY", "ADJACENT_ALLIES"}
    for a in data["abilities"]:
        assert a["mana_cost"] >= 0
        assert a["targeting"] in valid_targetings, \
            f"{a['id']}: неизвестный targeting {a['targeting']}"
        # хоть что-то должно происходить
        has_effect = bool(a.get("effect_specs"))
        has_damage = a.get("damage_percent", 0) > 0
        assert has_effect or has_damage, \
            f"{a['id']}: не наносит урон и не накладывает эффектов"


def test_every_hero_present_in_roster(settings):
    data = load_all(settings)
    expected = {"handswing", "smut", "mage", "healer", "tank",
                "assassin", "archer", "necromancer", "berserker", "paladin"}
    actual = {h["id"] for h in data["heroes"]}
    assert expected <= actual, f"Отсутствуют герои: {expected - actual}"


def test_ability_icons_unique_ids(settings):
    """Каждая способность — уникальный id (гарантия именования иконок)."""
    data = load_all(settings)
    ids = [a["id"] for a in data["abilities"]]
    assert len(ids) == len(set(ids))