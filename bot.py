import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN, TARIFFS
from database import (
    init_db, get_user, create_user, update_subscription,
    set_trial_used, add_payment, get_all_users
)
from github import get_servers, get_no_servers, save_subscription, build_profile

# ============================================================
# НАСТРОЙКА
# ============================================================

logging.basicConfig(level=logging.INFO)
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

# ============================================================
# КОМАНДЫ
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    create_user(user.id, user.username, user.first_name)
    
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

@dp.callback_query(lambda c: c.data == "trial")
async def trial(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Проверяем, не использовал ли уже
    user = get_user(user_id)
    if user and user[4]:  # trial_used
        await callback.answer("❌ Вы уже использовали пробный период!", show_alert=True)
        return
    
    # Проверяем, нет ли активной подписки
    if user and user[3] and user[3] != "trial":
        until = datetime.strptime(user[3], "%Y-%m-%d").date()  # Исправлено: user[3] - subscription_type, user[4] - subscription_until
        if until >= datetime.now().date():
            await callback.answer("❌ У вас уже есть активная подписка!", show_alert=True)
            return
    
    # Активируем пробный
    expire_date = datetime.now().date() + timedelta(days=3)
    expire_str = expire_date.strftime("%Y-%m-%d")
    
    update_subscription(user_id, "trial", expire_str)
    set_trial_used(user_id)
    
    # Генерируем файл подписки
    servers = get_servers()
    announce = f"🟢 Пробный период • до {expire_date.strftime('%d.%m.%Y')}"
    expire_ts = int(datetime.combine(expire_date, datetime.min.time()).timestamp())
    
    content = build_profile(announce, expire_ts, servers)
    link = save_subscription(user_id, content)
    
    await callback.message.edit_text(
        f"✅ **Пробный период активирован!**\n\n"
        f"📅 Действует до: {expire_date.strftime('%d.%m.%Y')}\n\n"
        f"🔗 **Ваша ссылка для подключения:**\n"
        f"`{link}`\n\n"
        f"📲 Скопируйте ссылку и вставьте в Hiddify/Nekobox",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статус", callback_data="status")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer("🎁 Пробный период активирован!")

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
    
    # Проверяем активную подписку
    user = get_user(user_id)
    if user and user[3]:
        until = datetime.strptime(user[3], "%Y-%m-%d").date()
        if until >= datetime.now().date():
            # Продлеваем
            new_until = until + timedelta(days=tariff["days"])
            update_subscription(user_id, tariff_key, new_until.strftime("%Y-%m-%d"))
            
            # Обновляем файл
            servers = get_servers()
            announce = f"🟢 {tariff['name']} • до {new_until.strftime('%d.%m.%Y')}"
            expire_ts = int(datetime.combine(new_until, datetime.min.time()).timestamp())
            content = build_profile(announce, expire_ts, servers)
            link = save_subscription(user_id, content)
            
            await callback.message.edit_text(
                f"✅ **Подписка ПРОДЛЕНА!**\n\n"
                f"📅 Новый срок: {new_until.strftime('%d.%m.%Y')}\n"
                f"🔗 Ссылка: `{link}`",
                parse_mode="Markdown"
            )
            await callback.answer("✅ Подписка продлена!")
            return
    
    # Новая подписка
    expire_date = datetime.now().date() + timedelta(days=tariff["days"])
    expire_str = expire_date.strftime("%Y-%m-%d")
    
    # Здесь должна быть интеграция с платежкой
    # Пока просто активируем (для теста)
    update_subscription(user_id, tariff_key, expire_str)
    
    servers = get_servers()
    announce = f"🟢 {tariff['name']} • до {expire_date.strftime('%d.%m.%Y')}"
    expire_ts = int(datetime.combine(expire_date, datetime.min.time()).timestamp())
    content = build_profile(announce, expire_ts, servers)
    link = save_subscription(user_id, content)
    
    await callback.message.edit_text(
        f"✅ **Тариф {tariff['name']} активирован!**\n\n"
        f"📅 Действует до: {expire_date.strftime('%d.%m.%Y')}\n"
        f"💰 Стоимость: {tariff['price']} ₽\n\n"
        f"🔗 Ссылка: `{link}`",
        parse_mode="Markdown"
    )
    await callback.answer(f"✅ {tariff['name']} активирован!")

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
    
    await message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="status")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ]),
        parse_mode="Markdown"
    )

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
# ЗАПУСК
# ============================================================

async def main():
    init_db()
    print("⚡ Магнит VPN бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())