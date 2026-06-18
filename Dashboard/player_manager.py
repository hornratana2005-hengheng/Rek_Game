import json
import os

FILE = "player_data.json"


def save_player_name(name):
    data = {"name": name}
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_player_name():
    if not os.path.exists(FILE):
        return None

    with open(FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("name")