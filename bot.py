import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ConversationHandler
)

# =========================
# Render FIX (порт-заглушка)
# =========================
port = int(os.environ.get("PORT", 10000))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("TOKEN")
ADMIN_ID = 123456789  # ⚠️ ВСТАВЬ СВОЙ TELEGRAM ID

# =========================
# ДАННЫЕ (каталог)
# =========================
PRODUCTS = {
    "p1": {"name": "💡 Лампочка", "price": 10000},
    "p2": {"name": "🔦 Фонарь", "price": 50000},
    "p3": {"name": "🔌 Розетка", "price": 15000},
}

ORDERS_FILE = "orders.json"

# =========================
# УТИЛИТЫ
# =========================
def load_orders():
    if not os.path.exists(ORDERS_FILE):
        return []
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_orders(orders):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

def get_cart(context: ContextTypes.DEFAULT_TYPE):
    if "cart" not in context.user_data:
        context.user_data["cart"] = {}
    return context.user_data["cart"]

def cart_total(cart):
    total = 0
    for pid, qty in cart.items():
        total += PRODUCTS[pid]["price"] * qty
    return total

def cart_text(cart):
    if not cart:
        return "🧺 Корзина пуста"
    lines = ["🧺 Ваша корзина:\n"]
    for pid, qty in cart.items():
        p = PRODUCTS[pid]
        lines.append(f"{p['name']} × {qty} = {p['price']*qty} сум")
    lines.append(f"\n💰 Итого: {cart_total(cart)} сум")
    return "\n".join(lines)

# =========================
# КАТАЛОГ (inline кнопки)
# =========================
def catalog_keyboard():
    kb = []
    for pid, p in PRODUCTS.items():
        kb.append([
            InlineKeyboardButton(
                f"{p['name']} — {p['price']} сум",
                callback_data=f"add:{pid}"
            )
        ])
    kb.append([InlineKeyboardButton("🧺 Открыть корзину", callback_data="open_cart")])
    return InlineKeyboardMarkup(kb)

def cart_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Продолжить покупки", callback_data="back_catalog")],
        [InlineKeyboardButton("🧹 Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton("🛒 Оформить заказ", callback_data="checkout")],
    ])

# =========================
# СЦЕНАРИЙ ОФОРМЛЕНИЯ
# =========================
ASK_PHONE, ASK_ADDRESS = range(2)

# =========================
# ХЕНДЛЕРЫ
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🤖 Магазин\nВыбери товар:"
    await update.message.reply_text(text, reply_markup=catalog_keyboard())

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    cart = get_cart(context)

    if data.startswith("add:"):
        pid = data.split(":")[1]
        cart[pid] = cart.get(pid, 0) + 1
        await query.edit_message_text(
            "✅ Добавлено в корзину\n\nВыбери ещё:",
            reply_markup=catalog_keyboard()
        )

    elif data == "open_cart":
        await query.edit_message_text(
            cart_text(cart),
            reply_markup=cart_keyboard()
        )

    elif data == "back_catalog":
        await query.edit_message_text(
            "📦 Каталог:",
            reply_markup=catalog_keyboard()
        )

    elif data == "clear_cart":
        context.user_data["cart"] = {}
        await query.edit_message_text("🧹 Корзина очищена", reply_markup=catalog_keyboard())

    elif data == "checkout":
        if not cart:
            await query.edit_message_text("Корзина пуста", reply_markup=catalog_keyboard())
            return ConversationHandler.END
        await query.message.reply_text("📱 Введите ваш номер телефона:")
        return ASK_PHONE

    return ConversationHandler.END

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    await update.message.reply_text("📍 Введите адрес доставки:")
    return ASK_ADDRESS

async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["address"] = update.message.text
    cart = get_cart(context)

    user = update.message.from_user
    order = {
        "user_id": user.id,
        "name": user.first_name,
        "username": user.username,
        "phone": context.user_data.get("phone"),
        "address": context.user_data.get("address"),
        "cart": cart,
        "total": cart_total(cart),
    }

    # сохранить
    orders = load_orders()
    orders.append(order)
    save_orders(orders)

    # отправить админу
    lines = [
        "🛒 НОВЫЙ ЗАКАЗ",
        f"👤 {order['name']} (@{order['username']})",
        f"📱 {order['phone']}",
        f"📍 {order['address']}",
        "\n📦 Товары:"
    ]
    for pid, qty in cart.items():
        p = PRODUCTS[pid]
        lines.append(f"{p['name']} × {qty} = {p['price']*qty} сум")
    lines.append(f"\n💰 Итого: {order['total']} сум")

    await context.bot.send_message(chat_id=ADMIN_ID, text="\n".join(lines))

    # очистить корзину
    context.user_data["cart"] = {}

    await update.message.reply_text("✅ Заказ оформлен! Мы скоро свяжемся с вами.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено")
    return ConversationHandler.END

# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(on_button, pattern="^checkout$")],
        states={
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_address)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(conv)

    print("🚀 BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
