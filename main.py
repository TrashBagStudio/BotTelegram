import asyncio
import json
import random
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8719296663:AAHVbDpT3q46i8dxCtR30hg5pcpPxWnOEaI"
ADMIN_ID = 6907865020  # <-- сюда свой ID

bot = Bot(TOKEN, parse_mode="Markdown")
dp = Dispatcher()

# ================== БАЗА ==================

def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_users():
    return load_json("users.json", {})

def load_services():
    return load_json("services.json", [])

def get_user(user_id, username):
    users = load_users()

    if str(user_id) not in users:
        users[str(user_id)] = {
            "username": username or "NoName",
            "balance": 0,
            "purchases": [],
            "transactions": []
        }
        save_json("users.json", users)

    return users[str(user_id)]

# ================== SAFE UI ==================

async def safe_edit(callback: CallbackQuery, image, text, kb):
    """Надежное обновление сообщения"""
    try:
        await callback.message.edit_media(
            InputMediaPhoto(
                media=FSInputFile(image),
                caption=text
            ),
            reply_markup=kb
        )
    except:
        try:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=kb
            )
        except:
            pass

# ================== КНОПКИ ==================

def main_menu_kb(user, is_admin=False):
    kb = InlineKeyboardBuilder()

    kb.button(text=f"💰 Баланс: {user['balance']}₽", callback_data="balance")
    kb.button(text="🏦 Купить", callback_data="buy")
    kb.button(text="🛟 Поддержка", callback_data="support")
    kb.button(text="📟 Промокоды", callback_data="promo")

    if user["purchases"]:
        kb.button(text="🧰 Покупки", callback_data="my_purchases")

    kb.button(text="📑 Инфо", callback_data="info")

    if is_admin:
        kb.button(text="➕ Добавить услугу", callback_data="add_service")

    kb.adjust(1, 2, 2, 1)
    return kb.as_markup()

def back_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅ Назад", callback_data="back")
    return kb.as_markup()

# ================== START ==================

@dp.message(CommandStart())
async def start(msg: Message):
    user = get_user(msg.from_user.id, msg.from_user.username)

    text = (
        f"👤 {user['username']}\n\n"
        f"📦 Покупки: {'есть' if user['purchases'] else 'нет'}\n\n"
        f"Выберите действие:"
    )

    await msg.answer_photo(
        FSInputFile("images/main.png"),
        caption=text,
        reply_markup=main_menu_kb(user, msg.from_user.id == ADMIN_ID)
    )

# ================== BACK ==================

@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    user = get_user(callback.from_user.id, callback.from_user.username)

    text = (
        f"👤 {user['username']}\n\n"
        f"📦 Покупки: {'есть' if user['purchases'] else 'нет'}\n\n"
        f"Выберите действие:"
    )

    await safe_edit(
        callback,
        "images/main.png",
        text,
        main_menu_kb(user, callback.from_user.id == ADMIN_ID)
    )

# ================== BUY ==================

@dp.callback_query(F.data == "buy")
async def buy(callback: CallbackQuery):
    services = load_services()

    if not services:
        return await callback.answer("Нет услуг", show_alert=True)

    kb = InlineKeyboardBuilder()

    text = "Выберите услугу:\n\n"

    for s in services:
        text += f"*{s['name']}* — {s['price']}₽\n"
        kb.button(text=s["name"], callback_data=f"service_{s['id']}")

    kb.button(text="⬅ Назад", callback_data="back")
    kb.adjust(1)

    await safe_edit(callback, "images/pay.png", text, kb.as_markup())

# ================== SERVICE ==================

@dp.callback_query(F.data.startswith("service_"))
async def service_view(callback: CallbackQuery):
    service_id = int(callback.data.split("_")[1])
    services = load_services()

    service = next((s for s in services if s["id"] == service_id), None)
    if not service:
        return await callback.answer("Услуга не найдена", show_alert=True)

    kb = InlineKeyboardBuilder()
    kb.button(text="Купить", callback_data=f"buy_{service_id}")
    kb.button(text="⬅ Назад", callback_data="buy")
    kb.adjust(1)

    text = (
        f"📟 *{service['name']}*\n\n"
        f"{service['description']}\n\n"
        f"💰 {service['price']}₽"
    )

    await safe_edit(callback, "images/pay.png", text, kb.as_markup())

# ================== PURCHASE ==================

@dp.callback_query(F.data.startswith("buy_"))
async def purchase(callback: CallbackQuery):
    service_id = int(callback.data.split("_")[1])

    users = load_users()
    services = load_services()

    user = users.get(str(callback.from_user.id))
    service = next((s for s in services if s["id"] == service_id), None)

    if not user or not service:
        return await callback.answer("Ошибка", show_alert=True)

    if user["balance"] < service["price"]:
        return await callback.answer("Недостаточно средств", show_alert=True)

    user["balance"] -= service["price"]
    user["purchases"].append(service["name"])
    user["transactions"].append(f"-{service['price']}₽")

    save_json("users.json", users)

    await safe_edit(
        callback,
        "images/pay.png",
        f"✅ Покупка успешна!\n\n{service['content']}",
        back_kb()
    )

# ================== BALANCE ==================

@dp.callback_query(F.data == "balance")
async def balance(callback: CallbackQuery):
    user = get_user(callback.from_user.id, callback.from_user.username)

    text = (
        f"💰 Баланс: {user['balance']}₽\n\n"
        f"Транзакции:\n"
        + "\n".join(user["transactions"][-3:] or ["нет"])
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Пополнить", callback_data="card")
    kb.button(text="⬅ Назад", callback_data="back")
    kb.adjust(1)

    await safe_edit(callback, "images/balance.png", text, kb.as_markup())

# ================== CARD ==================

@dp.callback_query(F.data == "card")
async def card(callback: CallbackQuery):
    code = random.randint(100000, 999999)

    text = f"Отправьте код для пополнения:\n\n`{code}`"

    await safe_edit(callback, "images/balance.png", text, back_kb())

# ================== SUPPORT ==================

@dp.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    text = (
        "🛟 *Поддержка*\n\n"
        "Если возникли проблемы — напишите:\n"
        "@yagram_sup_bot\n\n"
        "Ответ обычно в течение нескольких минут."
    )

    await safe_edit(callback, "images/support.png", text, back_kb())

# ================== INFO ==================

@dp.callback_query(F.data == "info")
async def info(callback: CallbackQuery):
    text = (
        "📑 *Информация*\n\n"
        "• Мгновенная выдача\n"
        "• Безопасные платежи\n"
        "• Анонимность\n\n"
        "Спасибо за использование ❤️"
    )

    await safe_edit(callback, "images/info.png", text, back_kb())

# ================== PROMO ==================

@dp.callback_query(F.data == "promo")
async def promo(callback: CallbackQuery):
    text = (
        "📟 *Промокоды*\n\n"
        "Введите промокод сообщением.\n\n"
        "Сейчас активных промокодов нет."
    )

    await safe_edit(callback, "images/promo.png", text, back_kb())

# ================== PURCHASES ==================

@dp.callback_query(F.data == "my_purchases")
async def my_purchases(callback: CallbackQuery):
    user = get_user(callback.from_user.id, callback.from_user.username)

    text = (
        "🧰 *Ваши покупки:*\n\n" +
        ("\n".join(user["purchases"]) if user["purchases"] else "нет")
    )

    await safe_edit(callback, "images/purchases.png", text, back_kb())

# ================== ADMIN ==================

adding_service = set()

@dp.callback_query(F.data == "add_service")
async def add_service(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Нет доступа", show_alert=True)

    adding_service.add(callback.from_user.id)

    await callback.message.answer(
        "Отправь JSON услуги:\n\n"
        '{ "id": 1, "name": "...", "description": "...", "price": 100, "content": "..." }'
    )

@dp.message()
async def handle_json(msg: Message):
    if msg.from_user.id not in adding_service:
        return

    try:
        data = json.loads(msg.text)

        required = {"id", "name", "description", "price", "content"}
        if not required.issubset(data):
            raise ValueError("Не все поля")

        services = load_services()
        services.append(data)

        save_json("services.json", services)

        adding_service.remove(msg.from_user.id)

        await msg.answer("✅ Услуга добавлена")

    except Exception as e:
        await msg.answer(f"❌ Ошибка:\n{e}")

# ================== RUN ==================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
