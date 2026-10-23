import os
import threading
import time
import requests
import io
import telebot
from telebot import types
from flask import Flask

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("BOT_TOKEN missing!")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

@app.route('/')
def home():
    return "Lucifer Bot Live"

# --- API ---
def get_spot_tickers():
    try:
        url = "https://api.bitget.com/api/v2/spot/market/tickers"
        r = requests.get(url, timeout=15)
        data = r.json()
        if data.get("code") == "00000":
            return data.get("data", [])
        return []
    except Exception as e:
        print(f"tickers error: {e}")
        return []

def get_candles(symbol, granularity="1h", limit=80):
    try:
        url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={granularity}&limit={limit}"
        r = requests.get(url, timeout=10)
        data = r.json()
        candles = data.get("data", [])
        return list(reversed(candles))
    except Exception as e:
        print(f"candles error {symbol}: {e}")
        return []

# --- CHART RED/GREEN CANDLES ---
def make_candle_image(symbol, granularity="1h"):
    candles = get_candles(symbol, granularity, 80)
    if len(candles) < 20:
        return None

    try:
        opens = [float(c[1]) for c in candles][-50:]
        highs = [float(c[2]) for c in candles][-50:]
        lows = [float(c[3]) for c in candles][-50:]
        closes = [float(c[4]) for c in candles][-50:]
    except Exception:
        return None

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor('#131722')
    ax.set_facecolor('#131722')

    for i in range(len(closes)):
        o = opens[i]
        h = highs[i]
        l = lows[i]
        c = closes[i]
        color = '#26a69a' if c >= o else '#ef5350'

        ax.plot([i, i], [l, h], color=color, linewidth=1)

        bottom = o if o < c else c
        height = abs(c - o)
        if height < 0.0000001:
            height = (h - l) * 0.05 if h != l else 0.01

        rect = mpatches.Rectangle((i-0.3, bottom), 0.6, height, facecolor=color, edgecolor=color)
        ax.add_patch(rect)

    ax.grid(True, color='#2a2e39', alpha=0.3, linestyle='--')
    ax.tick_params(colors='white')
    ax.yaxis.tick_right()

    for spine in ax.spines.values():
        spine.set_color('#2a2e39')

    ax.set_title(f"{symbol} {granularity}", color='white', fontsize=12, loc='left')
    ax.set_xlim(-1, len(closes))

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=200, facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf

def make_buttons(symbol):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_candle = types.InlineKeyboardButton("🕯️ Свечи", callback_data=f"chart_{symbol}")
    btn_bitget = types.InlineKeyboardButton("🟢 Bitget", url=f"https://www.bitget.com/spot/{symbol.replace('USDT','')}_USDT")
    btn_5m = types.InlineKeyboardButton("⏱️ 5м", callback_data=f"chart5m_{symbol}")
    btn_ref = types.InlineKeyboardButton(f"🔄 {symbol}", callback_data=f"refresh_{symbol}")
    markup.add(btn_candle, btn_bitget)
    markup.add(btn_5m, btn_ref)
    return markup

@bot.message_handler(commands=['start', 'scan', 'scan2'])
def handle_scan(m):
    try:
        is_scan2 = "scan2" in m.text
        thresh = 2 if is_scan2 else 4
        bot.send_message(m.chat.id, f"🔍 Ищу +{thresh}%...")

        tickers = get_spot_tickers()
        tickers = sorted(tickers, key=lambda x: float(x.get("change24h", 0)), reverse=True)

        count = 0
        for t in tickers:
            try:
                sym = t.get("symbol", "")
                if not sym.endswith("USDT"):
                    continue
                ch = float(t.get("change24h", 0)) * 100
                if ch < thresh or ch > 30:
                    continue
                txt = f"{'⚡' if is_scan2 else '🚀'} {sym} +{ch:.2f}%"
                bot.send_message(m.chat.id, txt, reply_markup=make_buttons(sym))
                count += 1
                if count >= 10:
                    break
            except Exception:
                continue
    except Exception as e:
        print(f"scan error: {e}")

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    try:
        d = call.data
        if d.startswith("chart_") and "chart5m" not in d:
            sym = d.replace("chart_", "")
            bot.answer_callback_query(call.id, f"Рисую {sym} 1ч")
            bot.send_chat_action(call.message.chat.id, 'upload_photo')
            img = make_candle_image(sym, "1h")
            if img:
                bot.send_photo(call.message.chat.id, img, caption=f"🕯️ {sym} 1H", reply_markup=make_buttons(sym))

        elif d.startswith("chart5m_"):
            sym = d.replace("chart5m_", "")
            bot.answer_callback_query(call.id)
            bot.send_chat_action(call.message.chat.id, 'upload_photo')
            img = make_candle_image(sym, "5m")
            if img:
                bot.send_photo(call.message.chat.id, img, caption=f"⏱️ {sym} 5м", reply_markup=make_buttons(sym))

        elif d.startswith("refresh_"):
            sym = d.replace("refresh_", "")
            bot.answer_callback_query(call.id)
            img = make_candle_image(sym, "1h")
            if img:
                bot.send_photo(call.message.chat.id, img, caption=f"🔄 {sym}", reply_markup=make_buttons(sym))
    except Exception as e:
        print(f"callback error: {e}")

def run_bot():
    while True:
        try:
            print("Starting polling...")
            bot.infinity_polling(timeout=90, long_polling_timeout=60, none_stop=True)
        except Exception as e:
            print(f"Polling exception (normal): {e} - restart in 5s")
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
