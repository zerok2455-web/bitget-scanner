import os
import threading
import time
import requests
import io
import telebot
from telebot import types
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

@app.route('/')
def home():
    return "Lucifer Scanner RU Final"

def get_spot_tickers():
    try:
        r = requests.get("https://api.bitget.com/api/v2/spot/market/tickers", timeout=15).json()
        return r.get("data", []) if r.get("code") == "00000" else []
    except:
        return []

def get_candles(symbol, gran="1h", limit=60):
    try:
        url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={gran}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        return list(reversed(r.get("data", [])))
    except:
        return []

def make_chart(symbol, gran="1h"):
    candles = get_candles(symbol, gran, 50)
    if len(candles) < 10:
        return None
    try:
        closes = [float(c[4]) for c in candles[-40:]]
        tickers = get_spot_tickers()
        ch24 = 0
        for t in tickers:
            if t['symbol'] == symbol:
                ch24 = float(t.get("change24h", 0)) * 100
                break
        
        color = "#00ff88" if ch24 >= 0 else "#ff4444"
        
        cfg = {
            "type": "line",
            "data": {
                "labels": [str(i) for i in range(len(closes))],
                "datasets": [{
                    "data": closes,
                    "borderColor": color,
                    "backgroundColor": "rgba(0,0,0,0)",
                    "fill": False,
                    "pointRadius": 0,
                    "borderWidth": 3,
                    "tension": 0.3
                }]
            },
            "options": {
                "title": {"display": True, "text": f"{symbol} {gran} {ch24:+.2f}% - Lucifer", "fontColor": "white", "fontSize": 16},
                "legend": {"display": False},
                "scales": {
                    "xAxes": [{"ticks": {"display": False}, "gridLines": {"color": "#2a2e39"}}],
                    "yAxes": [{"ticks": {"fontColor": "white"}, "gridLines": {"color": "#2a2e39"}}]
                }
            }
        }
        resp = requests.post(
            "https://quickchart.io/chart",
            json={"chart": cfg, "width": 800, "height": 400, "backgroundColor": "#131722", "format": "png"},
            timeout=20
        )
        if resp.status_code == 200 and len(resp.content) > 1000:
            buf = io.BytesIO(resp.content)
            buf.seek(0)
            return buf
        return None
    except Exception as e:
        print(f"chart err {e}")
        return None

def buttons(symbol):
    markup = types.InlineKeyboardMarkup(row_width=3)
    b1 = types.InlineKeyboardButton("📈 График", callback_data=f"chart_{symbol}")
    b2 = types.InlineKeyboardButton("🔗 Bitget", url=f"https://www.bitget.com/spot/{symbol.replace('USDT','')}_USDT")
    b3 = types.InlineKeyboardButton("⏱️ 5м", callback_data=f"chart5m_{symbol}")
    b4 = types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}")
    markup.add(b1, b2, b3)
    markup.add(b4)
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id,
        "👋 Привет! Я Lucifer Scanner\n\n"
        "Команды на русском:\n"
        "/scan - пампы от +4%\n"
        "/scan2 - ранние пампы от +2%\n"
        "/top5m - топ резких пампов за 5 минут\n"
        "/futures - фьючерсы (скоро)\n"
        "/funding - фандинг и упавшие монеты\n"
        "/calc - калькулятор\n"
        "/auto - авто-скан\n"
    )

@bot.message_handler(commands=['scan', 'scan2'])
def scan_cmd(m):
    is2 = "scan2" in m.text
    thresh = 2 if is2 else 4
    bot.send_message(m.chat.id, f"🔍 Ищу монеты от +{thresh}% за 24ч...")
    tickers = get_spot_tickers()
    tickers = sorted(tickers, key=lambda x: float(x.get("change24h", 0)), reverse=True)
    cnt = 0
    for t in tickers:
        try:
            sym = t['symbol']
            if not sym.endswith("USDT"): continue
            ch = float(t.get("change24h", 0)) * 
