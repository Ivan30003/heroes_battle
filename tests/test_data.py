from data.loader import load_all, load_settings


def test_settings_and_data_load():
    settings = load_settings("settings.json")
    data = load_all(settings)
    assert len(data["heroes"]) >= 2
    assert len(data["abilities"]) >= 1
    assert len(data["effects"]) >= 1
    assert len(data["passives"]) >= 1
    # ключевые персонажи из дизайн-дока
    assert "handswing" in data["index"]["heroes"]
    assert "smut" in data["index"]["heroes"]


def test_all_families_have_payload():
    settings = load_settings("settings.json")
    data = load_all(settings)
    for effect in data["effects"]:
        assert "payload" in effect and effect["payload"], (
            f"effect {effect['id']} без payload"
        )