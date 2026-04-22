import asyncio
import json
import random
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ================== CONFIG ==================
TOKEN = "8719296663:AAHVbDpT3q46i8dxCtR30hg5pcpPxWnOEaI"
ADMIN_ID = 6907865020  # <-- сюда свой I

DATA_DIR = Path(".")
USERS_FILE = DATA_DIR / "users.json"
SERVICES_FILE = DATA_DIR / "services.json"

logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN)
dp = Dispatcher()

# ================== UTILS ==================
def safe_load(path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Load error {path}: {e}")
        return default


def safe_save(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Save error {path}: {e}")


def load_users():
    return safe_load(USERS_FILE, {})


def save_users(data):
    safe_save(USERS_FILE, data)


def load_services():
    return safe_load(SERVICES_FILE, [])


def get_user(user_id, username):
    users = load_users()
    uid = str(user_id)

    if uid not in users:
        users[uid] = {
            "username": username or "NoName",
            "balance": 0,
            "purchases": [],
            "transactions": []
        }
        save_users(users)

    return users[uid]


# ================== UI ==================
async def edit_screen(callback: CallbackQuery, image, text, kb):
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=FSInputFile(image),
                caption=text,
                parse_mode="Markdown"
            ),
            reply_markup=kb
        )
    except Exception:
        try:
            await callback.message.edit_caption(text, reply_markup=kb)
        except Exception as e:
            logging.error(f"UI error: {e}")


# ================== KEYBOARDS ==================
def main_menu_kb(user, is_admin=False):
    kb = InlineKeyboardBuilder()

    kb.button(text=f"💰 {user['balance']}₽", callback_data="balance")
    kb.button(text="🏦 Купить", callback_data="buy")
    kb.button(text="🛟 Поддержка", callback_data="support")
    kb.button(text="📟 Промокоды", callback_data="promo")
    kb.button(text="📑 Инфо", callback_data="info")

    if user["purchases"]:
        kb.button(text="🧰 Покупки", callback_data="my_purchases")

    if is_admin:
        kb.button(text="➕ Услуга", callback_data="add_service")

    kb.adjust(1, 2, 2, 1)
    return kb.as_markup()


def services_kb(services):
    kb = InlineKeyboardBuilder()

    for s in services:
        kb.button(text=s["name"], callback_data=f"service_{s['id']}")

    kb.button(text="⬅ Назад", callback_data="back")
    kb.adjust(1)
    return kb.as_markup()


def service_action_kb(service_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="Купить", callback_data=f"buy_{service_id}")
    kb.button(text="⬅ Назад", callback_data="buy")
    kb.adjust(1)
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
        f"🪎 {'Нет покупок' if not user['purchases'] else 'Есть покупки'}\n\n"
        f"Выберите действие:"
    )

    await msg.answer_photo(
        photo=FSInputFile("images/main.png"),
        caption=text,
        reply_markup=main_menu_kb(user, msg.from_user.id == ADMIN_ID)
    )


# ================== BACK ==================
@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    user = get_user(callback.from_user.id, callback.from_user.username)

    text = (
        f"👤 {user['username']}\n\n"
        f"🪎 {'Нет покупок' if not user['purchases'] else 'Есть покупки'}\n\n"
        f"Выберите действие:"
    )

    await edit_screen(
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
        return await callback.answer("Нет доступных услуг", show_alert=True)

    text = "\n".join(
        f"*{s['name']}* — {s['price']}₽\n_{s['description']}_"
        for s in services
    )

    await edit_screen(
        callback,
        "images/pay.png",
        text,
        services_kb(services)
    )


# ================== VIEW SERVICE ==================
@dp.callback_query(F.data.startswith("service_"))
async def service_view(callback: CallbackQuery):
    service_id = int(callback.data.split("_")[1])
    services = load_services()

    service = next((s for s in services if s["id"] == service_id), None)

    if not service:
        return await callback.answer("Услуга не найдена", show_alert=True)

    text = (
        f"📟 {service['name']}\n\n"
        f"{service['description']}\n\n"
        f"💰 {service['price']}₽"
    )

    await edit_screen(
        callback,
        "images/pay.png",
        text,
        service_action_kb(service_id)
    )


# ================== PURCHASE ==================
@dp.callback_query(F.data.startswith("buy_"))
async def purchase(callback: CallbackQuery):
    service_id = int(callback.data.split("_")[1])

    users = load_users()
    services = load_services()

    uid = str(callback.from_user.id)
    user = users.get(uid)

    service = next((s for s in services if s["id"] == service_id), None)

    if not user or not service:
        return await callback.answer("Ошибка данных", show_alert=True)

    if user["balance"] < service["price"]:
        return await callback.answer("Недостаточно средств", show_alert=True)

    user["balance"] -= service["price"]
    user["purchases"].append(service["name"])
    user["transactions"].append(f"-{service['price']} ({service['name']})")

    save_users(users)

    await edit_screen(
        callback,
        "images/pay.png",
        f"✅ Успешно!\n\n{service['content']}",
        back_kb()
    )


# ================== ADMIN ADD ==================
adding_service = set()


@dp.callback_query(F.data == "add_service")
async def add_service(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Нет доступа", show_alert=True)

    adding_service.add(callback.from_user.id)

    await callback.message.edit_caption(
        "Отправь JSON услуги",
        reply_markup=back_kb()
    )


@dp.message()
async def handle_json(msg: Message):
    if msg.from_user.id not in adding_service:
        return

    try:
        data = json.loads(msg.text)

        required = {"id", "name", "description", "price", "content"}
        if not required.issubset(data):
            raise ValueError("Не все поля заполнены")

        services = load_services()
        services.append(data)
        safe_save(SERVICES_FILE, services)

        adding_service.remove(msg.from_user.id)

        await msg.answer("✅ Добавлено")

    except Exception as e:
        await msg.answer(f"Ошибка:\n{e}")


# ================== RUN ==================
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
