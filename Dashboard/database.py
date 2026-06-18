import sqlite3
import json

DB_NAME = "rek_game.db"


# =========================
# CONNECTION
# =========================
def connect_db():
    return sqlite3.connect(DB_NAME)


# =========================
# CREATE TABLES
# =========================
def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    # Player table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)

    # Save game table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS savegame(
        id INTEGER PRIMARY KEY,
        board TEXT,
        current_player TEXT,
        move_count INTEGER,
        seconds_elapsed INTEGER,
        mode TEXT
    )
    """)

    # History table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS game_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name TEXT,
        mode TEXT,
        result TEXT,
        played_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# =========================
# PLAYER NAME
# =========================
def save_player_name(name):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM player")

    cursor.execute(
        "INSERT INTO player(name) VALUES(?)",
        (name,)
    )

    conn.commit()
    conn.close()


def load_player_name():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM player
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    return row[0] if row else ""


# =========================
# SAVE / LOAD GAME
# =========================
def save_game_db(board, current_player, move_count, seconds_elapsed, mode):
    conn = connect_db()
    cursor = conn.cursor()

    board_json = json.dumps(board)

    cursor.execute("""
    INSERT OR REPLACE INTO savegame(
        id,
        board,
        current_player,
        move_count,
        seconds_elapsed,
        mode
    )
    VALUES(1,?,?,?,?,?)
    """, (
        board_json,
        current_player,
        move_count,
        seconds_elapsed,
        mode
    ))

    conn.commit()
    conn.close()


def load_game_db():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT board,
               current_player,
               move_count,
               seconds_elapsed,
               mode
        FROM savegame
        WHERE id = 1
    """)

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "board": json.loads(row[0]),
        "current_player": row[1],
        "move_count": row[2],
        "seconds_elapsed": row[3],
        "mode": row[4]
    }


# =========================
# HISTORY (WIN / LOSE)
# =========================
def save_history(player_name, mode, result):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO game_history(
        player_name,
        mode,
        result
    )
    VALUES(?,?,?)
    """, (
        player_name,
        mode,
        result
    ))

    conn.commit()
    conn.close()


def load_history():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT player_name,
           mode,
           result,
           played_at
    FROM game_history
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


# =========================
# STATS
# =========================
def get_stats(player_name=None):
    conn = connect_db()
    cursor = conn.cursor()

    if player_name:
        cursor.execute("""
        SELECT COUNT(*) FROM game_history
        WHERE result='WIN' AND player_name=?
        """, (player_name,))
        wins = cursor.fetchone()[0]

        cursor.execute("""
        SELECT COUNT(*) FROM game_history
        WHERE result='LOSE' AND player_name=?
        """, (player_name,))
        loses = cursor.fetchone()[0]

    else:
        cursor.execute("SELECT COUNT(*) FROM game_history WHERE result='WIN'")
        wins = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM game_history WHERE result='LOSE'")
        loses = cursor.fetchone()[0]

    conn.close()
    return wins, loses


# =========================
# TEST RUN
# =========================
if __name__ == "__main__":
    create_tables()

    save_player_name("Player1")

    save_history("Player1", "AI", "WIN")
    save_history("Player1", "AI", "LOSE")

    wins, loses = get_stats("Player1")

    print("Database Test")
    print("Wins:", wins)
    print("Loses:", loses)