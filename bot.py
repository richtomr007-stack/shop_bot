import os

print("🚀 BOT STARTED")

TOKEN = os.getenv("7960690278:AAE2rV3DO4xSs6cpijt6RYDFp_mz-9ce-PQ")

print("🔑 TOKEN =", TOKEN)

if not TOKEN:
    print("❌ TOKEN НЕ НАЙДЕН")
    exit()

print("✅ TOKEN НАЙДЕН, БОТ ГОТОВ")