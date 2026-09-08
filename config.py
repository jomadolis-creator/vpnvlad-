import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# ТЕЛЕГРАМ БОТ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# ============================================================
# GITHUB
# ============================================================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "magnit-vpn").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "subs").strip()
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip()

# ============================================================
# САЙТ ДЛЯ ПОДПИСОК
# ============================================================

PUBLIC_SITE_URL = os.getenv(
    "PUBLIC_SITE_URL",
    "https://magnitvpn.onrender.com"
).rstrip("/")

SUBSCRIPTION_PREFIX = os.getenv("SUBSCRIPTION_PREFIX", "magnit_").strip()

# ============================================================
# ФАЙЛЫ НА GITHUB
# ============================================================

SERVERS_FILE = "magnit_servers.txt"
NO_SERVERS_FILE = "magnit_no_servers.txt"

# ============================================================
# ТАРИФЫ (с ценами для Cashera)
# ============================================================

TARIFFS = {
    "trial": {
        "name": "🎁 Пробный",
        "days": 3,
        "price": 0,
        "description": "3 дня бесплатно"
    },
    "sbp_30": {
        "name": "💎 30 дней",
        "days": 30,
        "price": 129,
        "description": "1 месяц"
    },
    "sbp_90": {
        "name": "🔥 90 дней",
        "days": 90,
        "price": 379,
        "description": "3 месяца"
    },
    "sbp_180": {
        "name": "⚡ 180 дней",
        "days": 180,
        "price": 659,
        "description": "6 месяцев"
    },
    "sbp_365": {
        "name": "👑 365 дней",
        "days": 365,
        "price": 1089,
        "description": "1 год"
    }
}

# ============================================================
# CASHERA
# ============================================================

CASHERA_API_KEY = os.getenv("CASHERA_API_KEY", "").strip()
CASHERA_API_URL = os.getenv("CASHERA_API_URL", "https://api.cashera.io/v1").strip()
CASHERA_WEBHOOK_SECRET = os.getenv("CASHERA_WEBHOOK_SECRET", "").strip()

# ============================================================
# НАСТРОЙКИ
# ============================================================

PROFILE_TITLE = "𝗠𝗔𝗚𝗡𝗜𝗧 𝗩𝗣𝗡 ⚡️"
AUTO_SYNC_INTERVAL = 600  # 10 минут