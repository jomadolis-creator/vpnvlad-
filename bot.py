import asyncio
import logging
from datetime import datetime, timedelta
import uuid

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import (
    BOT_TOKEN, TARIFFS, 
    CASHERA_API_KEY, CASHERA_API_URL,
    PUBLIC_SITE_URL
)
from database import (
    init_db, get_user, create_user, update_subscription,
    set_trial_used, add_payment, get_payment, update_payment_status,
    get_all_users, get_active_users, get_stats
)
from github import (
    get_servers, get_no_servers, save_subscription, 
    build_profile, build_expired_profile, activate_subscription
)

# ============================================================
# НАСТРОЙКА
# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Пробный период", callback_data="trial")],
        [InlineKeyboardButton(text="💎 Купить подписку", callback_data="buy")],
        [InlineKeyboardButton(text="📊 Мой статус", callback_data="status")],
        [InlineKeyboardButton(text="📱 Как подключиться?", callback_data="howto")]
    ])

def tariff_buttons():
    buttons = []
    for key, tariff in TARIFFS.items():
        if key == "trial":
            continue
        price = f"{tariff['price']} ₽" if tariff['price'] > 0 else "Бесплатно"
        buttons.append([
            InlineKeyboardButton(
                text=f"{tariff['name']} — {price}",
                callback_data=f"tariff_{key}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_confirm(tariff_key: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить СБП", callback_data=f"pay_{tariff_key}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="buy")]
    ])

# ============================================================
# CASHERA API
# ============================================================

def create_cashera_payment(user_id: int, amount: int, days: int) -> dict:
    """Создает платеж в Cashera"""
    if not CASHERA_API_KEY:
        return {"error": "Cashera не настроена"}
    
    payment_id = f"magnit_{user_id}_{uuid.uuid4().hex[:8]}"
    
    # Формируем описание
    description = f"Магнит VPN - {days} дней"
    
    # Данные для платежа
    payload = {
        "amount": amount,
        "currency": "RUB",
        "description": description,
        "order_id": payment_id,
        "success_url": f"{PUBLIC_SITE_URL}/success",
        "fail_url": f"{PUBLIC_SITE_URL}/fail",
        "webhook_url": f"{PUBLIC_SITE_URL}/webhook/cashera"
    }
    
    headers = {
        "Authorization": f"Bearer {CASHERA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{CASHERA_API_URL}/payments",
            json=payload,
            headers=headers,
            timeout=30
        )
        return response.json()
    except Exception as e:
        logger.error(f"Cashera error: {e}")
        return {"error": str(e)}

# ============================================================
# КОМАНДЫ
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    create_user(user.id, user.username, user.first_name)
    
    # Проверяем статус
    db_user = get_user(user.id)
    if db_user and db_user[3]:
        try:
            until = datetime.strptime(db_user[4], "%Y-%m-%d").date()
            if until >= datetime.now().date():
                await message.answer(
                    "🟢 **У вас уже есть активная подписка!**\n"
                    f"📅 Действует до: {until.strftime('%d.%m.%Y')}\n\n"
                    "Используйте /status для просмотра",
                    parse_mode="Markdown"
                )
                return
        except:
            pass
    
    await message.answer(
        "⚡ **Добро пожаловать в Магнит VPN!**\n\n"
        "🌍 Быстрый и надежный VPN\n"
        "📲 Работает в Hiddify, Nekobox, v2rayNG\n\n"
        "Выберите действие:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    await show_status(message.from_user.id, message)

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Простая админка (только для владельца)"""
    # Проверяем, что это админ (замените на свой ID)
    ADMIN_IDS = [123456789]  # Ваш Telegram ID
    
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    stats = get_stats()
    
    text = (
        "📊 **Статистика Магнит VPN**\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🟢 Активных: {stats['active_users']}\n"
        f"💳 Платежей за месяц: {stats['payments_month']}\n"
        f"💰 Доход за месяц: {stats['revenue_month']} ₽\n"
    )
    
    await message.answer(text, parse_mode="Markdown")

# ============================================================
# КОЛБЭКИ
# ============================================================

@dp.callback_query(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⚡ **Главное меню**",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ---------- ПРОБНЫЙ ПЕРИОД ----------

@dp.callback_query(lambda c: c.data == "trial")
async def trial(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    user = get_user(user_id)
    if user and user[4]:  # trial_used
        await callback.answer("❌ Вы уже использовали пробный период!", show_alert=True)
        return
    
    if user and user[3]:
        try:
            until = datetime.strptime(user[4], "%Y-%m-%d").date()
            if until >= datetime.now().date():
                await callback.answer("❌ У вас уже есть активная подписка!", show_alert=True)
                return
        except:
            pass
    
    # Активируем пробный
    expire_date = datetime.now().date() + timedelta(days=3)
    expire_str = expire_date.strftime("%Y-%m-%d")
    
    update_subscription(user_id, "trial", expire_str)
    set_trial_used(user_id)
    
    servers = get_servers()
    announce = f"🟢 Пробный период • до {expire_date.strftime('%d.%m.%Y')}"
    expire_ts = int(datetime.combine(expire_date, datetime.min.time()).timestamp())
    
    content = build_profile(announce, expire_ts, servers)
    link = save_subscription(user_id, content)
    
    await callback.message.edit_text(
        f"✅ **Пробный период активирован!**\n\n"
        f"📅 Действует до: {expire_date.strftime('%d.%m.%Y')}\n\n"
        f"🔗 **Ваша ссылка:**\n"
        f"`{link}`\n\n"
        f"📲 Скопируйте и вставьте в Hiddify/Nekobox",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статус", callback_data="status")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer("🎁 Пробный период активирован!")

# ---------- ПОКУПКА ----------

@dp.callback_query(lambda c: c.data == "buy")
async def buy(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💎 **Выберите тариф:**\n\n"
        "Все тарифы дают доступ к одним и тем же серверам.\n"
        "Отличается только срок действия.",
        reply_markup=tariff_buttons(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("tariff_"))
async def process_tariff(callback: types.CallbackQuery):
    tariff_key = callback.data.replace("tariff_", "")
    tariff = TARIFFS.get(tariff_key)
    
    if not tariff:
        await callback.answer("❌ Тариф не найден")
        return
    
    user_id = callback.from_user.id
    
    # Проверяем, не пробный ли это
    if tariff_key == "trial":
        await trial(callback)
        return
    
    # Показываем подтверждение оплаты
    await callback.message.edit_text(
        f"💎 **{tariff['name']}**\n\n"
        f"📅 Срок: {tariff['days']} дней\n"
        f"💰 Цена: {tariff['price']} ₽\n\n"
        f"После оплаты подписка активируется автоматически.",
        reply_markup=payment_confirm(tariff_key),
        parse_mode="Markdown"
    )
    await callback.answer()

# ---------- ОПЛАТА ----------

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def process_payment(callback: types.CallbackQuery):
    tariff_key = callback.data.replace("pay_", "")
    tariff = TARIFFS.get(tariff_key)
    
    if not tariff:
        await callback.answer("❌ Тариф не найден")
        return
    
    user_id = callback.from_user.id
    amount = tariff["price"]
    days = tariff["days"]
    
    # Создаем платеж в Cashera
    try:
        result = create_cashera_payment(user_id, amount, days)
        
        if not result or "error" in result:
            await callback.message.answer(
                f"❌ Ошибка создания платежа: {result.get('error', 'Неизвестная ошибка')}\n\n"
                f"Попробуйте позже или обратитесь в поддержку."
            )
            await callback.answer()
            return
        
        payment_uuid = result.get("uuid") or result.get("id")
        payment_url = result.get("payment_url") or result.get("url")
        
        if not payment_uuid or not payment_url:
            await callback.message.answer(
                f"❌ Cashera вернула некорректный ответ.\n\n"
                f"Попробуйте позже."
            )
            await callback.answer()
            return
        
        # Сохраняем в БД
        add_payment(user_id, payment_uuid, tariff_key, amount, days)
        
        await callback.message.edit_text(
            f"💳 **Оплата через СБП**\n\n"
            f"📅 Тариф: {tariff['name']} ({days} дней)\n"
            f"💰 Сумма: {amount} ₽\n\n"
            f"🔗 **Ссылка на оплату:**\n"
            f"{payment_url}\n\n"
            f"⚠️ Не закрывайте страницу до завершения оплаты.\n"
            f"После оплаты подписка активируется автоматически.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{payment_uuid}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="buy")]
            ]),
            parse_mode="Markdown"
        )
        await callback.answer("💳 Платеж создан!")
        
    except Exception as e:
        logger.error(f"Payment error: {e}")
        await callback.message.answer(
            f"❌ Ошибка создания платежа.\n\n"
            f"Попробуйте позже."
        )
        await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery):
    payment_uuid = callback.data.replace("check_", "")
    payment = get_payment(payment_uuid)
    
    if not payment:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        return
    
    status = payment[5]  # status
    
    if status == "success":
        await callback.answer("✅ Оплата подтверждена!", show_alert=True)
        await show_status(callback.from_user.id, callback.message)
    else:
        await callback.answer("⏳ Платеж еще не обработан", show_alert=True)

# ---------- СТАТУС ----------

@dp.callback_query(lambda c: c.data == "status")
async def show_status_callback(callback: types.CallbackQuery):
    await show_status(callback.from_user.id, callback.message)
    await callback.answer()

async def show_status(user_id: int, message: types.Message):
    user = get_user(user_id)
    
    if not user or not user[3]:
        text = "🔴 **У вас нет активной подписки**\n\nИспользуйте /start чтобы выбрать тариф"
    else:
        sub_type = user[3]
        sub_until = user[4]
        
        try:
            until = datetime.strptime(sub_until, "%Y-%m-%d").date()
            today = datetime.now().date()
            days_left = (until - today).days
            
            if days_left < 0:
                text = f"🔴 **Подписка истекла** {until.strftime('%d.%m.%Y')}\n\nПродлите через /start"
                
                # Обновляем файл на заглушку
                content = build_expired_profile()
                save_subscription(user_id, content)
            else:
                tariff_name = TARIFFS.get(sub_type, {}).get("name", sub_type)
                text = (
                    f"🟢 **Подписка активна**\n\n"
                    f"📌 Тариф: {tariff_name}\n"
                    f"📅 Действует до: {until.strftime('%d.%m.%Y')}\n"
                    f"⏳ Осталось дней: {days_left}\n"
                )
        except:
            text = "❌ Ошибка даты подписки"
    
    try:
        await message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="status")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
            ]),
            parse_mode="Markdown"
        )
    except:
        pass

# ---------- КАК ПОДКЛЮЧИТЬСЯ ----------

@dp.callback_query(lambda c: c.data == "howto")
async def howto(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📱 **Как подключиться:**\n\n"
        "1️⃣ Скачайте приложение:\n"
        "• iOS: Hiddify / Shadowrocket\n"
        "• Android: Hiddify / v2rayNG\n"
        "• PC: Nekobox / v2rayN\n\n"
        "2️⃣ Скопируйте вашу ссылку из бота\n\n"
        "3️⃣ Вставьте ссылку в приложение\n\n"
        "4️⃣ Нажмите Connect 🚀",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

# ============================================================
# WEBHOOK ДЛЯ CASHERA
# ============================================================

@dp.message(Command("webhook"))
async def setup_webhook(message: types.Message):
    """Настройка webhook для Cashera"""
    ADMIN_IDS = [123456789]
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    webhook_url = f"{PUBLIC_SITE_URL}/webhook/cashera"
    
    # Отправляем в Cashera
    if CASHERA_API_KEY:
        try:
            response = requests.post(
                f"{CASHERA_API_URL}/webhooks",
                json={"url": webhook_url},
                headers={"Authorization": f"Bearer {CASHERA_API_KEY}"}
            )
            await message.answer(f"✅ Webhook настроен: {webhook_url}\n\nОтвет: {response.text}")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")
    else:
        await message.answer(f"⚠️ Вручную настройте webhook:\n{webhook_url}")

# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    init_db()
    
    # Запускаем бота
    logger.info("⚡ Магнит VPN бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())