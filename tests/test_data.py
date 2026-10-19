from data.loader import load_all, load_settings


def test_settings_and_data_load():
    settings = load_settings("settings.json")
    data = load_all(settings)
    assert len(data["heroes"]) >= 2
    assert "handswing" in data["index"]["heroes"]
    assert "smut" in data["index"]["heroes"]


def test_effects_have_payload():
    settings = load_settings("settings.json")
    data = load_all(settings)
    for effect in data["effects"]:
        assert effect.get("payload"), f"effect {effect['id']} без payload"
        for key in ("family", "stackable", "dispellable", "duration", "category"):
            assert key in effect, f"effect {effect['id']}: нет {key}"