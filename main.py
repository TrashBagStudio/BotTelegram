import asyncio
import json
import random

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
bot = Bot(TOKEN)
dp = Dispatcher()


# ================== БАЗА ==================
def load_users():
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_users(data):
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_services():
    try:
        with open("services.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def get_user(user_id, username):
    users = load_users()

    if str(user_id) not in users:
        users[str(user_id)] = {
            "username": username or "NoName",
            "balance": 0,
            "purchases": [],
            "transactions": []
        }
        save_users(users)

    return users[str(user_id)]


# ================== UI ==================
async def edit_screen(callback: CallbackQuery, image, text, kb):
    """Редактирование одного сообщения (картинка + текст + кнопки)"""
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=FSInputFile(image),
                caption=text,
                parse_mode="Markdown"
            ),
            reply_markup=kb
        )
    except Exception as e:
        print("edit_media error:", e)


# ================== КНОПКИ ==================
def main_menu_kb(user, is_admin=False):
    kb = InlineKeyboardBuilder()

    kb.button(text=f"💰Баланс: {user['balance']}", callback_data="balance")

    kb.button(text="🏦 Купить", callback_data="buy")
    kb.button(text="🛟 Поддержка", callback_data="support")

    if user["purchases"]:
        kb.button(text="📟 Промокоды", callback_data="promo")
        kb.button(text="🧰 Покупки", callback_data="my_purchases")
        kb.button(text="📑 Инфо", callback_data="info")
    else:
        kb.button(text="📟 Промокоды", callback_data="promo")
        kb.button(text="📑 Инфо", callback_data="info")

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
        f"👤 «{user['username']}»\n\n"
        f"🪎 «{'У вас нет покупок' if not user['purchases'] else 'Есть покупки'}»\n\n"
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
        f"👤 «{user['username']}»\n\n"
        f"🪎 «{'У вас нет покупок' if not user['purchases'] else 'Есть покупки'}»\n\n"
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

    text = "Выберите услугу:\n\n"

    for s in services:
        text += f"*_{s['name']}_* — {s['description']}, {s['price']}₽\n"

    await edit_screen(
        callback,
        "images/pay.png",
        text,
        services_kb(services)
    )


# ================== ПРОСМОТР УСЛУГИ ==================
@dp.callback_query(F.data.startswith("service_"))
async def service_view(callback: CallbackQuery):
    service_id = int(callback.data.split("_")[1])
    services = load_services()

    service = next(s for s in services if s["id"] == service_id)

    text = (
        f"📟 {service['name']}\n\n"
        f"Описание: «{service['description']}»\n\n"
        f"Цена: {service['price']}₽\n\n"
        f"Выберите действие:"
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

    user = users[str(callback.from_user.id)]
    service = next(s for s in services if s["id"] == service_id)

    if user["balance"] >= service["price"]:
        user["balance"] -= service["price"]
        user["purchases"].append(service["name"])
        user["transactions"].append(f"-{service['price']} ({service['name']})")

        save_users(users)

        await edit_screen(
            callback,
            "images/pay.png",
            f"✅ Покупка успешна!\n\n{service['content']}",
            back_kb()
        )
    else:
        await callback.answer("Недостаточно средств", show_alert=True)


# ================== БАЛАНС ==================
@dp.callback_query(F.data == "balance")
async def balance(callback: CallbackQuery):
    user = get_user(callback.from_user.id, callback.from_user.username)

    last = user["transactions"][-3:] if user["transactions"] else ["у вас нету транзакций"]

    text = (
        f"Ваш аккаунт: {user['username']}\n"
        f"Баланс: {user['balance']}₽\n\n"
        f"Последние транзакции: «{', '.join(last)}»\n\n"
        f"Выберите способ пополнения:"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Карта", callback_data="card")
    kb.button(text="⬅ Назад", callback_data="back")
    kb.adjust(1)

    await edit_screen(
        callback,
        "images/balance.png",
        text,
        kb.as_markup()
    )


# ================== ПОПОЛНЕНИЕ ==================
@dp.callback_query(F.data == "card")
async def card(callback: CallbackQuery):
    code = random.randint(100000, 999999)

    text = f"Ожидаем пополнение.\n\nОтправьте код:\n\n{code}"

    await edit_screen(
        callback,
        "images/balance.png",
        text,
        back_kb()
    )


# --- FSM state (простая переменная) ---
adding_service = {}

# --- support ---
@dp.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    text = "🛟 Поддержка:\n\nНапишите сюда: @yagram_sup_bot"

    await callback.message.edit_media(
        media=FSInputFile("images/support.png"),
        reply_markup=back_kb()
    )
    await callback.message.edit_caption(text)

# --- info ---
@dp.callback_query(F.data == "info")
async def info(callback: CallbackQuery):
    text = "📑 Информация:\n\nТут будет ваш текст (замени на нужный)."

    await callback.message.edit_media(
        media=FSInputFile("images/info.png"),
        reply_markup=back_kb()
    )
    await callback.message.edit_caption(text)

# --- promo ---
@dp.callback_query(F.data == "promo")
async def promo(callback: CallbackQuery):
    text = "📟 Промокоды\n\nРаздел временно недоступен."

    await callback.message.edit_media(
        media=FSInputFile("images/promo.png"),
        reply_markup=back_kb()
    )
    await callback.message.edit_caption(text)

# --- purchases ---
@dp.callback_query(F.data == "my_purchases")
async def my_purchases(callback: CallbackQuery):
    user = get_user(callback.from_user.id, callback.from_user.username)

    if user["purchases"]:
        text = "🧰 Ваши покупки:\n\n" + "\n".join(user["purchases"])
    else:
        text = "🧰 У вас нет покупок"

    await callback.message.edit_media(
        media=FSInputFile("images/purchases.png"),
        reply_markup=back_kb()
    )
    await callback.message.edit_caption(text)

# --- add service (admin) ---
@dp.callback_query(F.data == "add_service")
async def add_service(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Нет доступа", show_alert=True)

    adding_service[callback.from_user.id] = True

    await callback.message.edit_caption(
        "➕ Отправьте услугу в формате JSON:\n\n"
        '{\n'
        '  "id": 1,\n'
        '  "name": "Название",\n'
        '  "description": "Описание",\n'
        '  "price": 100,\n'
        '  "content": "Что получит пользователь"\n'
        '}',
        reply_markup=back_kb()
    )

# --- receive service JSON ---
@dp.message()
async def handle_service_json(msg: Message):
    if msg.from_user.id not in adding_service:
        return

    try:
        data = json.loads(msg.text)

        services = load_services()
        services.append(data)

        with open("services.json", "w", encoding="utf-8") as f:
            json.dump(services, f, indent=4, ensure_ascii=False)

        del adding_service[msg.from_user.id]

        await msg.answer("✅ Услуга добавлена", reply_markup=back_kb())

    except Exception as e:
        await msg.answer(f"❌ Ошибка JSON:\n{e}")


# ================== RUN ==================
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
