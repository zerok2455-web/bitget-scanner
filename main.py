import os, threading, time, requests, io
import telebot
from telebot import types
from flask import Flask
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

@app.route('/')
def home():
    return "Lucifer Bot Live - Chart Images ON"

def get_spot_tickers():
    try:
        r = requests.get("https://api.bitget.com/api/v2/spot/market/tickers", timeout=15).json()
        return r.get("data", []) if r.get("code")=="00000" else []
    except: return []

def get_candles(symbol, granularity="1h", limit=100):
    try:
        url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={granularity}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        data = r.get("data", [])
        return list(reversed(data))
    except: return []

def calc_rsi(prices, period=14):
    if len(prices) < period+1: return 50
    gains=losses=0
    for i in range(1, period+1):
        diff = prices[-i] - prices[-i-1]
        if diff>0: gains+=diff
        else: losses+=-diff
    if losses==0: return 70
    rs=gains/losses
    return 100 - (100/(1+rs))

def get_vol_spike(symbol):
    try:
        candles = get_candles(symbol, "1h", 21)
        if len(candles)>5:
            vols = [float(c[5]) for c in candles]
            avg_vol = sum(vols[:-1])/len(vols[:-1]) if len(vols)>1 else 0
            vol_spike = vols[-1]/avg_vol if avg_vol else 0
            return vol_spike
    except: pass
    return 0

def make_chart_image(symbol, granularity="1h"):
    candles = get_candles(symbol, granularity, 100)
    if len(candles)<20:
        return None
    closes = [float(c[4]) for c in candles]
    highs = [float(c[2]) for c in candles]
    lows = [float(c[3]) for c in candles]
    
    plt.figure(figsize=(10,4))
    plt.plot(closes, linewidth=1.5, label=symbol)
    plt.fill_between(range(len(closes)), lows, highs, alpha=0.1)
    plt.title(f"{symbol} {granularity} - Lucifer", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close()
    return buf

def make_buttons(symbol):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_img = types.InlineKeyboardButton("📈 График картинкой", callback_data=f"chart_{symbol}")
    btn_bitget = types.InlineKeyboardButton("🟢 Bitget", url=f"https://www.bitget.com/spot/{symbol.replace('USDT','')}_USDT")
    btn_5m = types.InlineKeyboardButton("⏱️ 5м", callback_data=f"chart5m_{symbol}")
    btn_refresh = types.InlineKeyboardButton(f"🔄 Обновить {symbol}", callback_data=f"refresh_{symbol}")
    markup.add(btn_img, btn_bitget)
    markup.add(btn_5m, btn_refresh)
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Lucifer 🔥 Готов\n/scan +4% RSI\n/scan2 +2%\n/top5m ранний памп\n/calc 100 20 4\nТеперь графики КАРТИНКАМИ!")

@bot.message_handler(commands=['scan','scan2'])
def scan_all(m):
    is_scan2 = "scan2" in m.text
    thresh = 2 if is_scan2 else 4
    bot.send_message(m.chat.id, f"🔍 Сканирую +{thresh}%...")
    tickers = get_spot_tickers()
    count=0
    for t in sorted(tickers, key=lambda x: float(x.get("change24h",0)), reverse=True):
        try:
            sym=t['symbol']
            if not sym.endswith("USDT"): continue
            ch=float(t.get("change24h",0))*100
            if ch<thresh or ch>25: continue
            candles=get_candles(sym, "1h", 30)
            closes=[float(c[4]) for c in candles] if candles else []
            rsi=calc_rsi(closes) if closes else 50
            spike=get_vol_spike(sym)
            txt=f"{'⚡' if is_scan2 else '🚀'} {sym} +{ch:.2f}% RSI {rsi:.1f} Vol x{spike:.1f}"
            bot.send_message(m.chat.id, txt, reply_markup=make_buttons(sym))
