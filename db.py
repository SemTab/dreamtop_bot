import sqlite3
from datetime import datetime

DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Таблица пользователей
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

    # Таблица криптовалют
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cryptocurrencies (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        symbol TEXT UNIQUE NOT NULL,
        current_price REAL NOT NULL,
        volatility REAL DEFAULT 0.1,
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Таблица портфелей пользователей
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_crypto_portfolio (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        crypto_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        average_buy_price REAL NOT NULL,
        FOREIGN KEY (user_id) REFERENCES accounts(id) ON DELETE CASCADE,
        FOREIGN KEY (crypto_id) REFERENCES cryptocurrencies(id) ON DELETE CASCADE,
        UNIQUE(user_id, crypto_id)
    )
    """)

    # Таблица истории цен криптовалют
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crypto_price_history (
        id INTEGER PRIMARY KEY,
        crypto_id INTEGER NOT NULL,
        price REAL NOT NULL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (crypto_id) REFERENCES cryptocurrencies(id) ON DELETE CASCADE
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

# ----------------- CRYPTOCURRENCY FUNCTIONS -----------------

def add_cryptocurrency(name: str, symbol: str, initial_price: float, volatility: float = 0.1, description: str = ""):
    """Добавляет новую криптовалюту в базу данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO cryptocurrencies (name, symbol, current_price, volatility, description)
        VALUES (?, ?, ?, ?, ?)
        """, (name, symbol, initial_price, volatility, description))
        crypto_id = cursor.lastrowid
        conn.commit()

        # Добавляем начальную запись в историю цен
        cursor.execute("""
        INSERT INTO crypto_price_history (crypto_id, price)
        VALUES (?, ?)
        """, (crypto_id, initial_price))
        conn.commit()

        return crypto_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_all_cryptocurrencies():
    """Получает все криптовалюты"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cryptocurrencies ORDER BY name")
    cryptos = cursor.fetchall()
    conn.close()
    return cryptos

def get_cryptocurrency(crypto_id: int):
    """Получает криптовалюту по ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cryptocurrencies WHERE id=?", (crypto_id,))
    crypto = cursor.fetchone()
    conn.close()
    return crypto

def get_cryptocurrency_by_symbol(symbol: str):
    """Получает криптовалюту по символу"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cryptocurrencies WHERE symbol=?", (symbol,))
    crypto = cursor.fetchone()
    conn.close()
    return crypto

def update_crypto_price(crypto_id: int, new_price: float):
    """Обновляет цену криптовалюты и добавляет запись в историю"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE cryptocurrencies SET current_price=? WHERE id=?", (new_price, crypto_id))

    # Добавляем запись в историю цен
    cursor.execute("""
    INSERT INTO crypto_price_history (crypto_id, price)
    VALUES (?, ?)
    """, (crypto_id, new_price))

    conn.commit()
    conn.close()

def get_crypto_price_history(crypto_id: int, limit: int = 24):
    """Получает историю цен криптовалюты (последние N записей)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT price, timestamp FROM crypto_price_history
    WHERE crypto_id=? ORDER BY timestamp DESC LIMIT ?
    """, (crypto_id, limit))
    history = cursor.fetchall()
    conn.close()
    return history

def get_user_portfolio(user_id: int):
    """Получает портфель криптовалют пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.amount, p.average_buy_price, c.id, c.name, c.symbol, c.current_price
    FROM user_crypto_portfolio p
    JOIN cryptocurrencies c ON p.crypto_id = c.id
    WHERE p.user_id=?
    """, (user_id,))
    portfolio = cursor.fetchall()
    conn.close()
    return portfolio

def buy_crypto(user_id: int, crypto_id: int, amount: float, price: float):
    """Покупает криптовалюту для пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем, есть ли уже эта крипта в портфеле
    cursor.execute("""
    SELECT amount, average_buy_price FROM user_crypto_portfolio
    WHERE user_id=? AND crypto_id=?
    """, (user_id, crypto_id))
    existing = cursor.fetchone()

    if existing:
        # Обновляем среднюю цену покупки
        current_amount, current_avg_price = existing
        new_amount = current_amount + amount
        new_avg_price = ((current_amount * current_avg_price) + (amount * price)) / new_amount

        cursor.execute("""
        UPDATE user_crypto_portfolio
        SET amount=?, average_buy_price=?
        WHERE user_id=? AND crypto_id=?
        """, (new_amount, new_avg_price, user_id, crypto_id))
    else:
        # Создаем новую запись в портфеле
        cursor.execute("""
        INSERT INTO user_crypto_portfolio (user_id, crypto_id, amount, average_buy_price)
        VALUES (?, ?, ?, ?)
        """, (user_id, crypto_id, amount, price))

    conn.commit()
    conn.close()

def sell_crypto(user_id: int, crypto_id: int, amount: float):
    """Продает криптовалюту пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT amount FROM user_crypto_portfolio
    WHERE user_id=? AND crypto_id=?
    """, (user_id, crypto_id))
    current = cursor.fetchone()

    if current and current[0] >= amount:
        new_amount = current[0] - amount
        if new_amount > 0:
            cursor.execute("""
            UPDATE user_crypto_portfolio
            SET amount=?
            WHERE user_id=? AND crypto_id=?
            """, (new_amount, user_id, crypto_id))
        else:
            cursor.execute("""
            DELETE FROM user_crypto_portfolio
            WHERE user_id=? AND crypto_id=?
            """, (user_id, crypto_id))

        conn.commit()
        conn.close()
        return True

    conn.close()
    return False

def get_portfolio_value(user_id: int):
    """Получает общую стоимость портфеля пользователя"""
    portfolio = get_user_portfolio(user_id)
    total_value = 0
    for amount, avg_price, crypto_id, name, symbol, current_price in portfolio:
        total_value += amount * current_price
    return total_value

def initialize_default_cryptocurrencies():
    """Инициализирует стандартный набор криптовалют"""
    default_cryptos = [
        ("Bitcoin", "BTC", 45000.0, 0.05, "Первая и самая популярная криптовалюта"),
        ("Ethereum", "ETH", 2800.0, 0.08, "Платформа для смарт-контрактов"),
        ("Binance Coin", "BNB", 320.0, 0.06, "Нативный токен биржи Binance"),
        ("Cardano", "ADA", 0.45, 0.12, "Блокчейн платформа третьего поколения"),
        ("Solana", "SOL", 95.0, 0.15, "Высокопроизводительная блокчейн платформа"),
        ("Dogecoin", "DOGE", 0.08, 0.20, "Мем-криптовалюта, созданная как шутка"),
        ("Polkadot", "DOT", 6.50, 0.10, "Мультичейн платформа для Web3"),
        ("Avalanche", "AVAX", 32.0, 0.13, "Платформа для децентрализованных приложений"),
        ("Chainlink", "LINK", 14.0, 0.09, "Децентрализованная сеть оракулов"),
        ("Polygon", "MATIC", 0.75, 0.11, "Решение для масштабирования Ethereum")
    ]

    for name, symbol, price, volatility, description in default_cryptos:
        # Проверяем, существует ли крипта
        existing = get_cryptocurrency_by_symbol(symbol)
        if not existing:
            add_cryptocurrency(name, symbol, price, volatility, description)

def update_all_crypto_prices():
    """Обновляет цены всех криптовалют согласно их волатильности"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, current_price, volatility FROM cryptocurrencies")
    cryptos = cursor.fetchall()

    for crypto_id, current_price, volatility in cryptos:
        # Генерируем случайное изменение цены (-volatility до +volatility)
        import random
        price_change = random.uniform(-volatility, volatility)
        new_price = max(0.01, current_price * (1 + price_change))  # Цена не может быть меньше 0.01

        update_crypto_price(crypto_id, round(new_price, 2))

    conn.close()