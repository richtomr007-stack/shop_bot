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
# SERVER (Render FIX)
# ========================
port = int(os.environ.get("PORT", 10000))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ========================
# CONFIG
# ========================
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

ORDERS_FILE = "orders.json"

# ========================
# AI (очень простой интеллект)
# ========================
def ai_answer(text):
    text = text.lower()

    if "что купить" in text:
        return "💡 Возьми лампочку или фонарь — это самое популярное"
    if "цена" in text:
        return "💰 Цены есть в каталоге, нажми /start"
    return "🤖 Я помогу тебе с заказом. Нажми /start"

# ========================
# PRODUCTS
# ========================
PRODUCTS = {
    "p1": {"name": "💡 Лампочка", "price": 10000},
    "p2": {"name": "🔦 Фонарь", "price": 50000},
    "p3": {"name": "🔌 Розетка", "price": 15000},
}

# ========================
# STORAGE
# ========================
def load_orders():
    if not os.path.exists(ORDERS_FILE):
        return []
    with open(ORDERS_FILE, "r") as f:
        return json.load(f)

def save_orders(data):
    with open(ORDERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ========================
# CART
# ========================
def get_cart(context):
    if "cart" not in context.user_data:
        context.user_data["cart"] = {}
    return context.user_data["cart"]

def total(cart):
    return sum(PRODUCTS[p]["price"] * q for p, q in cart.items())

# ========================
# KEYBOARDS
# ========================
def kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Товары", callback_data="cat")],
        [InlineKeyboardButton("🛒 Корзина", callback_data="cart")]
    ])

# ========================
# START
# ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛍 Магазин PRO++", reply_markup=kb())

# ========================
# BUTTONS
# ========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    cart = get_cart(context)

    if q.data == "cat":
        text = ""
        for pid, p in PRODUCTS.items():
            text += f"{p['name']} - {p['price']} сум\n"

        await q.edit_message_text(text)

    elif q.data == "cart":
        if not cart:
            await q.edit_message_text("Пусто")
        else:
            text = "\n".join(
                f"{PRODUCTS[p]['name']} x{qnt}"
                for p, qnt in cart.items()
            )
            text += f"\n\n💰 {total(cart)} сум"
            text += "\n\nНапиши номер телефона для заказа"

            await q.edit_message_text(text)

# ========================
# TEXT (AI + ORDER FIX)
# ========================
async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_msg = update.message.text
    cart = get_cart(context)

    # если это телефон
    if text_msg.isdigit() or text_msg.startswith("+"):

        order = {
            "name": update.message.from_user.first_name,
            "phone": text_msg,
            "items": cart,
            "total": total(cart)
        }

        orders = load_orders()
        orders.append(order)
        save_orders(orders)

        # админу
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🛒 Новый заказ:\n{order}"
        )

        context.user_data["cart"] = {}

        await update.message.reply_text("✅ Заказ принят!")
        return

    # AI ответ
    reply = ai_answer(text_msg)
    await update.message.reply_text(reply)

# ========================
# ADMIN
# ========================
async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    data = load_orders()
    text = "📊 Заказы:\n\n"

    for i, o in enumerate(data[-10:], 1):
        text += f"{i}. {o['name']} | {o['phone']} | {o['total']} сум\n"

    await update.message.reply_text(text)

# ========================
# MAIN
# ========================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", orders))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

    print("🚀 PRO+++ BOT STARTED")
    app.run_polling()

if __name__ == "__main__":
    main()
