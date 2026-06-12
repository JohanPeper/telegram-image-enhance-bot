import sqlite3
import os

DB_PATH = "payments.db"

# Старые функции (для Stripe, оставляем, не используются)
def init_db_old():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS payments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  session_id TEXT UNIQUE,
                  file_id TEXT,
                  status TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def add_payment(session_id, user_id, file_id, status='pending'):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO payments (session_id, user_id, file_id, status) VALUES (?, ?, ?, ?)",
              (session_id, user_id, file_id, status))
    conn.commit()
    conn.close()

def update_payment_status(session_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE payments SET status = ? WHERE session_id = ?", (status, session_id))
    conn.commit()
    conn.close()

def get_payment(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, file_id, status FROM payments WHERE session_id = ?", (session_id,))
    row = c.fetchone()
    conn.close()
    return row

# Новая функция инициализации для Stars
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stars_payments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  stars_amount INTEGER,
                  file_id TEXT,
                  status TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
    # создаём старую таблицу тоже (на всякий случай)
    init_db_old()

def save_payment(user_id, stars_amount, status, file_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO stars_payments (user_id, stars_amount, file_id, status) VALUES (?, ?, ?, ?)",
              (user_id, stars_amount, file_id, status))
    conn.commit()
    conn.close()