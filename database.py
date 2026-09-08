import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

DB_NAME = "magnit.db"

# ============================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            subscription_type TEXT,
            subscription_until TEXT,  -- YYYY-MM-DD
            trial_used BOOLEAN DEFAULT FALSE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            tariff_key TEXT,
            payment_id TEXT UNIQUE,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ База готова")

# ============================================================
# ПОЛЬЗОВАТЕЛИ
# ============================================================

def get_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

def create_user(user_id: int, username: str = None, first_name: str = None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (user_id, username, first_name))
    conn.commit()
    conn.close()

def update_subscription(user_id: int, sub_type: str, until: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET subscription_type = ?, subscription_until = ?
        WHERE user_id = ?
    """, (sub_type, until, user_id))
    conn.commit()
    conn.close()

def set_trial_used(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET trial_used = TRUE WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()

def add_payment(user_id: int, amount: int, tariff: str, payment_id: str, status: str = "pending"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO payments (user_id, amount, tariff_key, payment_id, status)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, amount, tariff, payment_id, status))
    conn.commit()
    conn.close()

def update_payment_status(payment_id: str, status: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE payments SET status = ? WHERE payment_id = ?
    """, (status, payment_id))
    conn.commit()
    conn.close()