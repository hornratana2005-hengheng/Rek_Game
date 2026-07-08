import json
import os

from Dashboard.database import connect_db, create_tables, load_player_name as load_db_player_name, save_player_name as save_db_player_name

FILE = "player_data.json"


def save_player_name(name):
    create_tables()
    clean_name = (name or "").strip()
    if clean_name:
        save_db_player_name(clean_name)

    data = {"name": clean_name}
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

    return clean_name


def load_player_name():
    create_tables()

    db_name = load_db_player_name()
    if db_name:
        data = {"name": db_name}
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return db_name

    return None


def clear_player_name():
    create_tables()

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM player")
    conn.commit()
    conn.close()

    if os.path.exists(FILE):
        os.remove(FILE)

    return True