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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            payment_id TEXT UNIQUE,
            tariff_key TEXT,
            amount INTEGER,
            days INTEGER,
            status TEXT DEFAULT 'pending',  -- pending, success, failed
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ База данных готова")

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
    cursor.execute("SELECT * FROM users ORDER BY user_id")
    users = cursor.fetchall()
    conn.close()
    return users

def get_active_users():
    today = datetime.now().date().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM users 
        WHERE subscription_type IS NOT NULL 
        AND subscription_until >= ?
        AND subscription_type != 'trial'
    """, (today,))
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
        SET subscription_type = ?, 
            subscription_until = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (sub_type, until, user_id))
    conn.commit()
    conn.close()

def set_trial_used(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET trial_used = TRUE, updated_at = CURRENT_TIMESTAMP 
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()

# ============================================================
# ПЛАТЕЖИ
# ============================================================

def add_payment(user_id: int, payment_id: str, tariff_key: str, amount: int, days: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO payments (user_id, payment_id, tariff_key, amount, days, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    """, (user_id, payment_id, tariff_key, amount, days))
    conn.commit()
    conn.close()

def get_payment(payment_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
    payment = cursor.fetchone()
    conn.close()
    return payment

def update_payment_status(payment_id: str, status: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE payments 
        SET status = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE payment_id = ?
    """, (status, payment_id))
    conn.commit()
    conn.close()

def get_pending_payments():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payments WHERE status = 'pending'")
    payments = cursor.fetchall()
    conn.close()
    return payments

# ============================================================
# СТАТИСТИКА
# ============================================================

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    
    today = datetime.now().date().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT COUNT(*) FROM users 
        WHERE subscription_type IS NOT NULL 
        AND subscription_until >= ?
    """, (today,))
    active = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT SUM(amount) FROM payments 
        WHERE status = 'success' 
        AND created_at >= date('now', '-30 days')
    """)
    revenue = cursor.fetchone()[0] or 0
    
    cursor.execute("""
        SELECT COUNT(*) FROM payments 
        WHERE status = 'success' 
        AND created_at >= date('now', '-30 days')
    """)
    payments_count = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "total_users": total,
        "active_users": active,
        "revenue_month": revenue,
        "payments_month": payments_count
    }