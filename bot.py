import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ========================
# RENDER FIX (порт)
# ========================
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

# ========================
# CONFIG
# ========================
TOKEN = os.getenv("7960690278:AAE2rV3DO4xSs6cpijt6RYDFp_mz-9ce-PQ")
ADMIN_ID = int(os.getenv("8712749134", "0"))

# ========================
# PRODUCTS
# ========================
PRODUCTS = {
    "p1": {"name": "💡 Лампочка", "price": 10000},
    "p2": {"name": "🔦 Фонарь", "price": 50000},
    "p3": {"name": "🔌 Розетка", "price": 15000},
}

# ========================
# CART
# ========================
def get_cart(context):
    if "cart" not in context.user_data:
        context.user_data["cart"] = {}
    return context.user_data["cart"]

def cart_total(cart):
    return sum(PRODUCTS[p]["price"] * q for p, q in cart.items())

# ========================
# KEYBOARDS
# ========================
def catalog_keyboard():
    kb = []
    for pid, p in PRODUCTS.items():
        kb.append([
            InlineKeyboardButton(f"{p['name']} - {p['price']} сум", callback_data=f"add:{pid}")
        ])
    kb.append([InlineKeyboardButton("🧺 Корзина", callback_data="cart")])
    return InlineKeyboardMarkup(kb)

def cart_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧹 Очистить", callback_data="clear")],
        [InlineKeyboardButton("🛒 Оформить", callback_data="checkout")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

# ========================
# START
# ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 Магазин:", reply_markup=catalog_keyboard())

# ========================
# BUTTONS
# ========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    cart = get_cart(context)
    data = q.data

    if data.startswith("add:"):
        pid = data.split(":")[1]
        cart[pid] = cart.get(pid, 0) + 1
        await q.edit_message_text("Добавлено ✔", reply_markup=catalog_keyboard())

    elif data == "cart":
        if not cart:
            text = "🧺 Корзина пустая"
        else:
            text = "\n".join(
                f"{PRODUCTS[p]['name']} x{qnt}"
                for p, qnt in cart.items()
            )
            text += f"\n\n💰 Итого: {cart_total(cart)} сум"

        await q.edit_message_text(text, reply_markup=cart_keyboard())

    elif data == "clear":
        context.user_data["cart"] = {}
        await q.edit_message_text("🧹 Очищено", reply_markup=catalog_keyboard())

    elif data == "back":
        await q.edit_message_text("📦 Магазин:", reply_markup=catalog_keyboard())

    elif data == "checkout":
        await q.message.reply_text("📱 Напиши номер телефона:")

# ========================
# TEXT HANDLER
# ========================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    cart = get_cart(context)

    # заказ (простая версия)
    if text.startswith("+") or text.isdigit():
        user = update.message.from_user

        order_text = (
            f"🛒 НОВЫЙ ЗАКАЗ\n\n"
            f"👤 {user.first_name}\n"
            f"📱 {text}\n\n"
        )

        for p, qnt in cart.items():
            order_text += f"{PRODUCTS[p]['name']} x{qnt}\n"

        order_text += f"\n💰 Итого: {cart_total(cart)} сум"

        await context.bot.send_message(chat_id=ADMIN_ID, text=order_text)

        context.user_data["cart"] = {}

        await update.message.reply_text("✅ Заказ принят!")
    else:
        await update.message.reply_text("Используй кнопки 🙂")

# ========================
# MAIN
# ========================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🚀 BOT STARTED")
    app.run_polling()

if __name__ == "__main__":
    main()
