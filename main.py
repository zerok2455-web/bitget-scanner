import os
import telebot
from telebot import types
from flask import Flask, request
import requests
import time

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

try:
    bot.set_my_commands([
        types.BotCommand("start", "🚀 Главное меню"),
        types.BotCommand("scan", "🚀 Пампы от 4%"),
        types.BotCommand("scan2", "⚡ Ранние пампы от 2%"),
        types.BotCommand("top5m", "🔥 Топ за 5 минут"),
    ])
except:
    pass

def get_tickers():
    try:
        r = requests.get("https://api.bitget.com/api/v2/spot/market/tickers", timeout=10).json()
        return r.get('data', [])
    except:
        return []

def format_signal(symbol, price, change, vol):
    entry = price
    stop = price * 0.975
    tp1 = price * 1.03
    tp2 = price * 1.06
    tp3 = price * 1.10
    if price < 0.01:
        f = lambda x: f"{x:.8f}"
    else:
        f = lambda x: f"{x:.4f}"
    
    return f"""💎 <b>{symbol}</b> +{change:.2f}%

🎯 <b>ВХОД:</b> {f(entry)}
🛑 <b>СТОП:</b> {f(stop)} (-2.5%)
✅ <b>ТЕЙК 1:</b> {f(tp1)} (+3%)
✅ <b>ТЕЙК 2:</b> {f(tp2)} (+6%)
✅ <b>ТЕЙК 3:</b> {f(tp3)} (+10%)

📊 Цена: {f(price)}
💰 Объем: {vol:,.0f}
"""

@bot.message_handler(commands=['start'])
def start(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🚀 СКАН", "⚡ СКАН 2")
    kb.add("🔥 ТОП 5М")
    bot.send_message(m.chat.id, "👋 Готов! Жми кнопку:", reply_markup=kb, parse_mode="HTML")

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    txt = m.text or ""
    is_early = "2" in txt
    thresh = 2.0 if is_early or "scan2" in txt else 4.0
    if "СКАН" not in txt and "scan" not in txt and "ТОП" not in txt:
        return
    bot.send_message(m.chat.id, f"🔍 Сканирую от {thresh}%...")
    tickers = get_tickers()
    c = 0
    for t in tickers:
        try:
            sym = t['symbol']
            if "USDT" not in sym: continue
            ch = float(t.get('change24h', 0)) * 100
            pr = float(t['lastPr'])
            vol = float(t.get('quoteVolume', 0))
            if ch >= thresh and vol > 50000:
                msg = format_signal(sym, pr, ch, vol)
                markup = types.InlineKeyboardMarkup()
                clean = sym.replace("/", "")
                markup.add(types.InlineKeyboardButton("📈 График", url=f"https://www.tradingview.com/chart/?symbol=BITGET%3A{clean}"))
                bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=markup)
                c+=1
                if c>=8: break
                time.sleep(0.3)
        except: continue
    if c==0:
        bot.send_message(m.chat.id, "😴 Пока пусто, попробуй ⚡ СКАН 2")

@app.route('/')
def home():
    return "Live OK"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'ok'

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
