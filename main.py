import asyncio
import json
import random
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InputMediaPhoto
)
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8719296663:AAHVbDpT3q46i8dxCtR30hg5pcpPxWnOEaI"
ADMIN_ID = 6907865020  # <-- сюда свой ID

bot = Bot(TOKEN, parse_mode="Markdown")
dp = Dispatcher()

USERS_FILE = Path("users.json")
SERVICES_FILE = Path("services.json")

# ================== БАЗА ==================
def load_json(path, default):
    try:
        if not path.exists():
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_users():
    return load_json(USERS_FILE, {})


def save_users(data):
    save_json(USERS_FILE, data)


def load_services():
    return load_json(SERVICES_FILE, [])


def save_services(data):
    save_json(SERVICES_FILE, data)


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
                caption=text
            ),
            reply_markup=kb
        )
    except Exception as e:
        print("edit_screen error:", e)

    await callback.answer()


async def simple_page(callback, image, text):
    await edit_screen(callback, image, text, back_kb())


# ================== КНОПКИ ==================
def main_menu_kb(user, is_admin=False):
    kb = InlineKeyboardBuilder()

    kb.button(text=f"💰Баланс: {user['balance']}", callback_data="balance")
    kb.button(text="🏦 Купить", callback_data="buy")
    kb.button(text="🛟 Поддержка", callback_data="support")

    kb.button(text="📟 Промокоды", callback_data="promo")
    kb.button(text="📑 Инфо", callback_data="info")

    if user["purchases"]:
        kb.button(text="🧰 Покупки", callback_data="my_purchases")

    if is_admin:
        kb.button(text="➕ Добавить услугу", callback_data="add_service")

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
        f"👤 *{user['username']}*\n\n"
        f"🪎 {'Нет покупок' if not user['purchases'] else 'Есть покупки'}\n\n"
        f"Выберите действие:"
    )

    await msg.answer_photo(
        photo=FSInputFile("images/main.png"),
        caption=text,
        reply_markup=main_menu_kb(user, msg.from_user.id == ADMIN_ID)
    )


# ================== НАЗАД ==================
@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    user = get_user(callback.from_user.id, callback.from_user.username)

    text = (
        f"👤 *{user['username']}*\n\n"
        f"🪎 {'Нет покупок' if not user['purchases'] else 'Есть покупки'}\n\n"
        f"Выберите действие:"
    )

    await edit_screen(
        callback,
        "images/main.png",
        text,
        main_menu_kb(user, callback.from_user.id == ADMIN_ID)
    )


# ================== КУПИТЬ ==================
@dp.callback_query(F.data == "buy")
async def buy(callback: CallbackQuery):
    services = load_services()

    if not services:
        return await callback.answer("Нет услуг", show_alert=True)

    text = "*Выберите услугу:*\n\n"

    for s in services:
        text += f"*{s['name']}* — {s['price']}₽\n_{s['description']}_\n\n"

    await edit_screen(callback, "images/pay.png", text, services_kb(services))


# ================== ПРОСМОТР УСЛУГИ ==================
@dp.callback_query(F.data.startswith("service_"))
async def service_view(callback: CallbackQuery):
    service_id = int(callback.data.split("_")[1])
    services = load_services()

    service = next((s for s in services if s["id"] == service_id), None)
    if not service:
        return await callback.answer("Услуга не найдена", show_alert=True)

    text = (
        f"*{service['name']}*\n\n"
        f"{service['description']}\n\n"
        f"💰 {service['price']}₽"
    )

    await edit_screen(
        callback,
        "images/pay.png",
        text,
        service_action_kb(service_id)
    )


# ================== ПОКУПКА ==================
@dp.callback_query(F.data.startswith("buy_"))
async def purchase(callback: CallbackQuery):
    service_id = int(callback.data.split("_")[1])

    users = load_users()
    services = load_services()

    uid = str(callback.from_user.id)

    if uid not in users:
        return await callback.answer("Ошибка пользователя", show_alert=True)

    user = users[uid]
    service = next((s for s in services if s["id"] == service_id), None)

    if not service:
        return await callback.answer("Услуга не найдена", show_alert=True)

    if user["balance"] < service["price"]:
        return await callback.answer("Недостаточно средств", show_alert=True)

    user["balance"] -= service["price"]
    user["purchases"].append(service["name"])
    user["transactions"].append(f"-{service['price']} ({service['name']})")

    save_users(users)

    await edit_screen(
        callback,
        "images/pay.png",
        f"✅ *Покупка успешна!*\n\n{service['content']}",
        back_kb()
    )


# ================== БАЛАНС ==================
@dp.callback_query(F.data == "balance")
async def balance(callback: CallbackQuery):
    user = get_user(callback.from_user.id, callback.from_user.username)

    last = user["transactions"][-3:] or ["Нет транзакций"]

    text = (
        f"*Баланс:* {user['balance']}₽\n\n"
        f"*История:*\n" + "\n".join(last)
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Карта", callback_data="card")
    kb.button(text="⬅ Назад", callback_data="back")
    kb.adjust(1)

    await edit_screen(callback, "images/balance.png", text, kb.as_markup())


# ================== ПОПОЛНЕНИЕ ==================
@dp.callback_query(F.data == "card")
async def card(callback: CallbackQuery):
    code = random.randint(100000, 999999)

    text = f"*Ожидаем оплату*\n\nКод:\n`{code}`"

    await edit_screen(callback, "images/balance.png", text, back_kb())


# ================== СТРАНИЦЫ ==================
@dp.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    await simple_page(
        callback,
        "images/support.png",
        "🛟 *Поддержка*\n\n@your_support"
    )


@dp.callback_query(F.data == "info")
async def info(callback: CallbackQuery):
    await simple_page(
        callback,
        "images/info.png",
        "📑 *Информация*\n\nВаш текст"
    )


@dp.callback_query(F.data == "promo")
async def promo(callback: CallbackQuery):
    await simple_page(
        callback,
        "images/promo.png",
        "📟 *Промокоды*\n\nСкоро..."
    )


@dp.callback_query(F.data == "my_purchases")
async def my_purchases(callback: CallbackQuery):
    user = get_user(callback.from_user.id, callback.from_user.username)

    text = "*Ваши покупки:*\n\n"
    text += "\n".join(user["purchases"]) if user["purchases"] else "Пусто"

    await simple_page(callback, "images/purchases.png", text)


# ================== АДМИН ==================
adding_service = {}


@dp.callback_query(F.data == "add_service")
async def add_service(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Нет доступа", show_alert=True)

    adding_service[callback.from_user.id] = True

    await callback.message.answer(
        "Отправь JSON услуги",
        reply_markup=back_kb()
    )


@dp.message()
async def handle_service_json(msg: Message):
    if msg.from_user.id not in adding_service:
        return

    try:
        data = json.loads(msg.text)

        services = load_services()
        services.append(data)
        save_services(services)

        del adding_service[msg.from_user.id]

        await msg.answer("✅ Услуга добавлена")

    except Exception as e:
        await msg.answer(f"Ошибка JSON:\n{e}")


# ================== RUN ==================
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
