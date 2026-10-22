import os
from threading import Thread
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is alive"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
Thread(target=run_web, daemon=True).start()
import telebot, requests, os
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
def get_tickers():
    try:
        r=requests.get("https://api.bitget.com/api/v2/spot/market/tickers",timeout=10).json()
        return r.get("data",[]) if r.get("code")=="00000" else []
    except: return []
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "✅ Бот 24/7 работает!\n/scan - пампы\n/price BTC")
@bot.message_handler(commands=['scan'])
def scan(m):
    tickers=get_tickers()
    pumps=[]
    for t in tickers:
        s=t.get("symbol","")
        if not s.endswith("USDT"): continue
        try:
            vol=float(t.get("quoteVolume",0))
            if vol<50000: continue
            ch=float(t.get("changeUtc24h",0))*100
            if 5<=ch<=90:
                pumps.append((s,ch,t.get("lastPr")))
        except: continue
    pumps.sort(key=lambda x:x[1],reverse=True)
    if not pumps:
        bot.send_message(m.chat.id,"Пампов нет 😴")
        return
    msg="🔥 Пампы Bitget:\n\n"
    for s,c,p in pumps[:15]:
        msg+=f"{s} +{c:.1f}% — {p}\n"
    bot.send_message(m.chat.id,msg)
@bot.message_handler(commands=['price'])
def price(m):
    try:
        coin=m.text.split()[1].upper()
        if not coin.endswith("USDT"): coin+="USDT"
        r=requests.get(f"https://api.bitget.com/api/v2/spot/market/tickers?symbol={coin}",timeout=5).json()
        t=r["data"][0]
        bot.send_message(m.chat.id,f"{coin}: {t['lastPr']}$ ({float(t['changeUtc24h'])*100:+.1f}%)")
    except:
        bot.send_message(m.chat.id,"Пиши: /price BTC")
bot.infinity_polling()
import telebot, requests, os, time

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# --- НАСТРОЙКИ ФИЛЬТРА ---
MIN_PERCENT = 12  # минимум +12%
MIN_VOL_24H = 1000000  # минимум $1M объем
COOLDOWN = 1800  # 30 мин не слать одну монету
BLACKLIST = ["USDC", "USDT", "BTC", "ETH", "BGB"]
last_sent = {}

def get_tickers():
    try:
        r = requests.get("https://api.bitget.com/api/v2/spot/market/tickers", timeout=10)
        return r.json().get("data", [])
    except:
        return []

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "✅ Бот 24/7 работает!\n/scan - пампы\n/price BTC")

@bot.message_handler(commands=['scan'])
def scan_cmd(m):
    bot.reply_to(m, "🔍 Сканирую...")
    do_scan(m.chat.id)

def do_scan(chat_id=None):
    tickers = get_tickers()
    found = []
    for t in tickers:
        try:
            symbol = t['symbol']
            if any(b in symbol for b in BLACKLIST): continue
            if not symbol.endswith("USDT"): continue
            
            change = float(t.get('change24h', 0)) * 100
            vol = float(t.get('quoteVolume', 0) or t.get('usdtVolume', 0))
            price = float(t.get('lastPr', 0))

            if price < 0.0001: continue
            if change < MIN_PERCENT: continue
            if vol < MIN_VOL_24H: continue

            # анти-спам
            if symbol in last_sent and time.time() - last_sent[symbol] < COOLDOWN:
                continue

            last_sent[symbol] = time.time()
            found.append(f"🚀 {symbol} {change:.1f}% | Vol ${vol/1e6:.1f}M")
        except:
            continue
    
    if found:
        text = "🔥 Пампы Bitget (фильтр $1M+):\n\n" + "\n".join(found[:10])
    else:
        text = "Сейчас чистых пампов нет (фильтр $1M+ отсеял мусор)"
    
    # если вызвано по команде
    if chat_id:
        bot.send_message(chat_id, text)
    # если вызвано авто-сканером - сюда твой CHAT_ID
    # else: bot.send_message(ТВОЙ_CHAT_ID, text)

# Авто-скан каждые 2 мин
bot.remove_webhook()
print("Сканер запущен...")

while True:
    try:
        do_scan()
        time.sleep(120)
    except Exception as e:
        print(e)
        time.sleep(10)

# bot.infinity_polling() - не нужно, у нас while
import telebot, requests, os, time
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

MIN_PERCENT = 12
MIN_VOL_24H = 1000000
COOLDOWN = 1800
BLACKLIST = ["USDCUSDT", "BTCUSDT", "ETHUSDT", "BGBUSDT"]
last_sent = {}

def get_tickers():
    try:
        r = requests.get("https://api.bitget.com/api/v2/spot/market/tickers", timeout=10)
        return r.json().get("data", [])
    except:
        return []

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "✅ Бот 24/7 работает!\n/scan - пампы с кнопками\n/price BTC")

@bot.message_handler(commands=['scan'])
def scan_cmd(m):
    bot.reply_to(m, "🔍 Сканирую с фильтром $1M+...")
    do_scan(m.chat.id)

def do_scan(chat_id=None):
    tickers = get_tickers()
    count = 0
    for t in tickers:
        try:
            symbol = t['symbol']
            if symbol in BLACKLIST: continue
            if not symbol.endswith("USDT"): continue
            
            change = float(t.get('change24h', 0)) * 100
            vol = float(t.get('quoteVolume', 0) or t.get('usdtVolume', 0) or 0)
            price = float(t.get('lastPr', 0) or 0)

            if price < 0.0001: continue
            if change < MIN_PERCENT: continue
            if vol < MIN_VOL_24H: continue
            if symbol in last_sent and time.time() - last_sent[symbol] < COOLDOWN:
                continue

            last_sent[symbol] = time.time()
            
            # --- КНОПКИ ---
            markup = types.InlineKeyboardMarkup()
            btn1 = types.InlineKeyboardButton("📈 Bitget", url=f"https://www.bitget.com/spot/{symbol}")
            # TradingView - убираем USDT для поиска
            base = symbol.replace("USDT","")
            btn2 = types.InlineKeyboardButton("📊 TradingView", url=f"https://www.tradingview.com/symbols/{base}USDT/")
            markup.add(btn1, btn2)

            text = f"🚀 <b>{symbol}</b>\n+{change:.2f}% за 24ч\nVol: ${vol/1e6:.1f}M\nЦена: {price}"

            # Куда слать
            target = chat_id if chat_id else m.chat.id if 'm' in locals() else None
            if chat_id:
                bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
            count += 1
            if count >= 8: break # не спамим больше 8 за раз

        except Exception as e:
            print(e)
            continue
    
    if chat_id and count == 0:
        bot.send_message(chat_id, "Сейчас чистых пампов нет. Фильтр $1M отсеял весь шлак 👍")

bot.remove_webhook()
print("Сканер с кнопками запущен...")

# Запускаем и команды и авто-скан
import threading
def auto_loop():
    while True:
        try:
            do_scan(chat_id=int(os.getenv("CHAT_ID", "0")) or None)
            time.sleep(120)
        except:
            time.sleep(10)

# если у тебя есть CHAT_ID в переменных Render - авто-скан будет слать туда
if os.getenv("CHAT_ID"):
    threading.Thread(target=auto_loop, daemon=True).start()

bot.infinity_polling(none_stop=True, timeout=60)
