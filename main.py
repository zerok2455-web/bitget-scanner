import os
import telebot
from telebot import types
from flask import Flask
import requests
import threading
import time

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- Меню ---
try:
    bot.set_my_commands([
        types.BotCommand("start", "🚀 Главное меню"),
        types.BotCommand("scan", "🚀 Пампы от 4%"),
        types.BotCommand("scan2", "⚡ Ранние пампы от 2%"),
        types.BotCommand("top5m", "🔥 Топ за 5 минут"),
        types.BotCommand("funding", "💰 Фандинг"),
    ])
except:
    pass

def get_tickers():
    try:
        url = "https://api.bitget.com/api/v2/spot/market/tickers"
        r = requests.get(url, timeout=10).json()
        return r.get('data', [])
    except:
        return []

def format_signal(symbol, price, change, volume):
    # Расчет
    entry = price
    stop = price * 0.975
    tp1 = price * 1.03
    tp2 = price * 1.06
    tp3 = price * 1.10
    
    if price < 0.01:
        f = "{:.8f}".format
    elif price < 1:
        f = "{:.6f}".format
    else:
        f = "{:.4f}".format

    text = f"""💎 <b>{symbol}</b> +{change:.2f}%

🎯 <b>ВХОД:</b> {f(entry)}
🛑 <b>СТОП:</b> {f(stop)} (-2.5%)
✅ <b>ТЕЙК 1:</b> {f(tp1)} (+3%)
✅ <b>ТЕЙК 2:</b> {f(tp2)} (+6%)
✅ <b>ТЕЙК 3:</b> {f(tp3)} (+10%)

📊 Цена: ${f(price)}
💰 Объем 24ч: ${volume:,.0f}
⚡ Риск/Профит: 1 к 4
"""
    return text

@bot.message_handler(commands=['start'])
def start(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🚀 СКАН", "⚡ СКАН 2", "🔥 ТОП 5М")
    bot.send_message(m.chat.id, "
