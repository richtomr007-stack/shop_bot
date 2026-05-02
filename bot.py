import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("7960690278:AAE2rV3DO4xSs6cpijt6RYDFp_mz-9ce-PQ")

print("STARTING BOT...")

if not TOKEN:
    print("TOKEN NOT FOUND")
    raise Exception("No TOKEN in environment variables")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот работает на Render")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

def main():
    print("BOT INITIALIZING...")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()