import requests
import base64
from datetime import datetime
from config import (
    GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, GITHUB_BRANCH,
    PUBLIC_SITE_URL, SUBSCRIPTION_PREFIX,
    SERVERS_FILE, NO_SERVERS_FILE, PROFILE_TITLE
)

# ============================================================
# ЗАГРУЗКА ФАЙЛОВ С GITHUB
# ============================================================

def download_file(filename: str) -> str:
    url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{filename}"
    response = requests.get(url, timeout=10)
    
    if response.status_code != 200:
        raise Exception(f"Не могу скачать {filename}: {response.status_code}")
    
    content = response.text.strip()
    if not content:
        raise Exception(f"Файл {filename} пустой")
    
    return content

def get_servers() -> str:
    """VLESS-ссылки для активных подписчиков"""
    return download_file(SERVERS_FILE)

def get_no_servers() -> str:
    """Пустой файл для неактивных"""
    return download_file(NO_SERVERS_FILE)

# ============================================================
# ЗАГРУЗКА НА GITHUB
# ============================================================

def upload_file(filename: str, content: str) -> bool:
    if not GITHUB_TOKEN:
        print("⚠️ Нет GITHUB_TOKEN")
        return False
    
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Получаем SHA
    response = requests.get(url, headers=headers)
    sha = response.json().get("sha") if response.status_code == 200 else None
    
    data = {
        "message": f"Update {filename}",
        "content": base64.b64encode(content.encode()).decode(),
        "branch": GITHUB_BRANCH
    }
    if sha:
        data["sha"] = sha
    
    response = requests.put(url, headers=headers, json=data)
    return response.status_code in (200, 201)

def save_subscription(user_id: int, content: str) -> str:
    """Сохраняет персональный файл подписки"""
    filename = f"{SUBSCRIPTION_PREFIX}{user_id}.txt"
    upload_file(filename, content)
    return f"{PUBLIC_SITE_URL}/s/{SUBSCRIPTION_PREFIX}{user_id}"

# ============================================================
# ПОСТРОЕНИЕ ПРОФИЛЯ
# ============================================================

def build_profile(announce: str, expire_timestamp: int, servers: str) -> str:
    lines = [
        f"# {PROFILE_TITLE}",
        f"# {announce}",
        f"# expire={expire_timestamp}",
        "# upload=0",
        "# download=0",
        "# total=0",
        "",
        servers
    ]
    return "\n".join(lines)

def build_expired_profile() -> str:
    """Профиль для истекшей подписки"""
    no_servers = get_no_servers()
    lines = [
        f"# {PROFILE_TITLE}",
        "# 🔴 Подписка истекла",
        "# expire=0",
        "# upload=0",
        "# download=0",
        "# total=0",
        "",
        no_servers
    ]
    return "\n".join(lines)

def activate_subscription(user_id: int, tariff_key: str, days: int) -> str:
    """Активирует подписку и возвращает ссылку"""
    from config import TARIFFS
    
    tariff = TARIFFS.get(tariff_key)
    if not tariff:
        raise Exception(f"Тариф {tariff_key} не найден")
    
    # Рассчитываем дату
    expire_date = datetime.now().date()
    
    # Если уже есть подписка - продлеваем
    from database import get_user
    user = get_user(user_id)
    if user and user[3]:  # subscription_type
        try:
            current_until = datetime.strptime(user[4], "%Y-%m-%d").date()
            if current_until > expire_date:
                expire_date = current_until
        except:
            pass
    
    expire_date = expire_date + timedelta(days=days)
    expire_str = expire_date.strftime("%Y-%m-%d")
    
    # Обновляем в БД
    from database import update_subscription
    update_subscription(user_id, tariff_key, expire_str)
    
    # Генерируем файл
    servers = get_servers()
    announce = f"🟢 {tariff['name']} • до {expire_date.strftime('%d.%m.%Y')}"
    expire_ts = int(datetime.combine(expire_date, datetime.min.time()).timestamp())
    
    content = build_profile(announce, expire_ts, servers)
    return save_subscription(user_id, content)