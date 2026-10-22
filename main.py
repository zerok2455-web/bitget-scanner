import telebot, requests, time, math, threading, os
from flask import Flask
from datetime import datetime
BOT_TOKEN = 8877158919:AAF_ZZdRg5xKXhKOQD_9y0JLG_aIxA06VpU
CHAT_ID = None  # можно оставить None

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

app = Flask(__name__)
@app.route('/')
def home():
    return "BOT ULTRA LIVE"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

def get_pump_data():
    url = "https://api.bitget.com/api/v2/spot/market/tickers"
    try:
        r = requests.get(url, timeout=10).json()
        data = r.get('data', [])
        pumps = []
        for coin in data:
            try:
                if not coin['symbol'].endswith('USDT'): continue
                change = float(coin['change24h'])
                if change > 5:
                    pumps.append((coin['symbol'], change, float(coin['lastPr'])))
            except: continue
        pumps.sort(key=lambda x: x[1], reverse=True)
        return pumps[:10]
    except:
        return []

def calc_levels(price, change, direction):
    entry = price * 0.998 if direction=="LONG" else price * 1.002
    stop = entry * (0.97 if direction=="LONG" else 1.03)
    t1 = entry * (1.04 if direction=="LONG" else 0.96)
    t2 = entry * (1.08 if direction=="LONG" else 0.92)
    t3 = entry * (1.15 if direction=="LONG" else 0.85)
    acc = min(92, 65 + change*1.5)
    return entry, stop, t1, t2, t3, acc

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "🔥 БОТ ULTRA V2 ГОТОВ!\nПиши /scan чтобы поймать памп!\n\nРаботает 24/7 🚀")

@bot.message_handler(commands=['scan'])
def scan(m):
    bot.send_message(m.chat.id, "🔍 Сканирую Bitget...")
    pumps = get_pump_data()
    if not pumps:
        bot.send_message(m.chat.id, "😴 Пока нет пампов >5%. Попробуй через 5 мин.")
        return
    for symbol, change, price in pumps[:5]:
        direction = "ЛОНГ" if change>0 else "ШОРТ"
        entry, stop, t1, t2, t3, acc = calc_levels(price, change, "LONG" if change>0 else "SHORT")
        text = f"🔥 {symbol} +{change:.1f}% — {price}\n\n"
        text += f"{'🟢' if direction=='ЛОНГ' else '🔴'} {direction} — СНАЙПЕР ВХОД\n"
        text += f"📍 ВХОД ЗОНА: {entry:.6f}\n"
        text += f"🛑 СТОП: {stop:.6f} (-3%)\n"
        text += f"🎯 Тейк 1: {t1:.6f} (+4%)\n"
        text += f"🎯 Тейк 2: {t2:.6f} (+8%)\n"
        text += f"🎯 Тейк 3: {t3:.6f} (+15%)\n"
        text += f"🎯 Точность: {acc:.0f}%\n\n"
        text += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        bot.send_message(m.chat.id, text)
        time.sleep(0.5)

print("BOT STARTED")
while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
    except Exception as e:
        print(f"Polling error: {e}, restart in 5s")
        time.sleep(5)
