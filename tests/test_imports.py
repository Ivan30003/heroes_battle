"""Автопроверка правила зависимостей."""
import os


def _scan(folder: str, forbidden: str) -> list[str]:
    hits = []
    for root, _, files in os.walk(folder):
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            with open(p, encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, 1):
                    if forbidden in line:
                        hits.append(f"{p}:{line_no}: {line.strip()}")
    return hits


def test_core_does_not_import_pygame():
    hits = _scan("core", "pygame")
    assert not hits, "core/ не должен импортировать pygame:\n" + "\n".join(hits)


def test_view_does_not_import_core():
    hits = _scan("view", "import core") + _scan("view", "from core")
    assert not hits, "view/ не должен импортировать core:\n" + "\n".join(hits)