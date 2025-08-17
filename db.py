import sqlite3
from datetime import datetime

DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        coins INTEGER DEFAULT 0,
        last_reward TEXT,
        ban_until TEXT,
        ban_reason TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO accounts (id, username, last_reward) VALUES (?, ?, ?)",
                       (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, coins, last_reward, ban_until, ban_reason FROM accounts WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id: int):
    return get_user(user_id)

def get_user_by_username(username: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, coins, last_reward, ban_until, ban_reason FROM accounts WHERE username=?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_coins(user_id: int, coins: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE accounts SET coins=? WHERE id=?", (coins, user_id))
    conn.commit()
    conn.close()

def update_last_reward(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE accounts SET last_reward=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()
    conn.close()

def transfer_coins(sender_id: int, recipient_id: int, amount: int):
    sender = get_user(sender_id)
    recipient = get_user(recipient_id)
    if sender and recipient and sender[2] >= amount:
        update_coins(sender_id, sender[2] - amount)
        update_coins(recipient_id, recipient[2] + amount)
        return True
    return False

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, coins FROM accounts ORDER BY coins DESC LIMIT 10")
    users = cursor.fetchall()
    conn.close()
    return users

# ----------------- BAN -----------------
def update_ban(user_id: int, until, reason: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE accounts SET ban_until=?, ban_reason=? WHERE id=?", (until, reason, user_id))
    conn.commit()
    conn.close()

def check_ban(user_id: int):
    user = get_user(user_id)
    if not user:
        return False, None, ""
    ban_until, reason = user[4], user[5]
    if not ban_until:
        return False, None, ""
    if ban_until == "forever":
        return True, "навсегда", reason
    until_dt = datetime.strptime(ban_until, "%Y-%m-%d %H:%M:%S")
    if until_dt > datetime.now():
        return True, ban_until, reason
    return False, None, ""
#--------------------------------------------------------------------------------------------------
def get_any_user_by_id(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_any_user_by_username(username: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def unban_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE accounts SET ban_until = NULL, ban_reason = NULL WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()