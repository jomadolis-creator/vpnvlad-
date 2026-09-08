import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# ТЕЛЕГРАМ БОТ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# ============================================================
# GITHUB (хостинг для файлов подписки)
# ============================================================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "ваш_логин").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "vpn-subs").strip()
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip()

# ============================================================
# САЙТ ДЛЯ ПОДПИСОК
# ============================================================

PUBLIC_SITE_URL = os.getenv(
    "PUBLIC_SITE_URL",
    "https://ваш-сайт.onrender.com"
).rstrip("/")

SUBSCRIPTION_PREFIX = os.getenv("SUBSCRIPTION_PREFIX", "magnit_").strip()

# ============================================================
# ФАЙЛЫ НА GITHUB
# ============================================================

# Файл с рабочими VLESS-ссылками (для активных подписчиков)
SERVERS_FILE = "magnit_servers.txt"

# Файл-заглушка (для неактивных)
NO_SERVERS_FILE = "magnit_no_servers.txt"

# ============================================================
# ТАРИФЫ (только сроки, без серверов)
# ============================================================

TARIFFS = {
    "trial": {
        "name": "🎁 Пробный",
        "days": 3,
        "price": 0,
        "description": "3 дня"
    },
    "lite": {
        "name": "💎 Лайт",
        "days": 30,
        "price": 299,
        "description": "1 месяц"
    },
    "standard": {
        "name": "🔥 Стандарт",
        "days": 60,
        "price": 499,
        "description": "2 месяца"
    },
    "vip": {
        "name": "👑 VIP",
        "days": 90,
        "price": 799,
        "description": "3 месяца"
    }
}

# ============================================================
# ПЛАТЕЖИ (заглушка)
# ============================================================

PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "mock").strip()