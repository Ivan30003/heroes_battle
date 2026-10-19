import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from data.loader import load_all, load_settings


@pytest.fixture(scope="session")
def settings():
    return load_settings("settings.json")


@pytest.fixture(scope="session")
def game_data(settings):
    return load_all(settings)