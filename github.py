import requests
import base64
from config import (
    GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, GITHUB_BRANCH,
    PUBLIC_SITE_URL, SUBSCRIPTION_PREFIX,
    SERVERS_FILE, NO_SERVERS_FILE
)

# ============================================================
# ЗАГРУЗКА ФАЙЛОВ
# ============================================================

def download_file(filename: str) -> str:
    """Скачивает файл с GitHub"""
    url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{filename}"
    response = requests.get(url, timeout=10)
    
    if response.status_code != 200:
        raise Exception(f"Не могу скачать {filename}: {response.status_code}")
    
    content = response.text.strip()
    if not content:
        raise Exception(f"Файл {filename} пустой")
    
    return content

def get_servers() -> str:
    """Возвращает содержимое magnit_servers.txt (VLESS-ссылки)"""
    return download_file(SERVERS_FILE)

def get_no_servers() -> str:
    """Возвращает заглушку для неактивных"""
    return download_file(NO_SERVERS_FILE)

# ============================================================
# ЗАГРУЗКА НА GITHUB
# ============================================================

def upload_file(filename: str, content: str) -> bool:
    """Загружает файл на GitHub"""
    if not GITHUB_TOKEN:
        print("⚠️ Нет GITHUB_TOKEN")
        return False
    
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Получаем SHA если файл есть
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
    """Сохраняет персональную подписку пользователя"""
    filename = f"{SUBSCRIPTION_PREFIX}{user_id}.txt"
    upload_file(filename, content)
    return f"{PUBLIC_SITE_URL}/s/{SUBSCRIPTION_PREFIX}{user_id}"

# ============================================================
# ПОСТРОЕНИЕ ПРОФИЛЯ
# ============================================================

def build_profile(announce: str, expire_timestamp: int, servers: str) -> str:
    """Собирает файл подписки для Hiddify/Nekobox"""
    lines = [
        "# 𝗠𝗔𝗚𝗡𝗜𝗧 𝗩𝗣𝗡 ⚡️",
        f"# {announce}",
        f"# expire={expire_timestamp}",
        "# upload=0",
        "# download=0",
        "# total=0",
        "",
        servers
    ]
    return "\n".join(lines)