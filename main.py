import os, threading, time, requests, io
import telebot
from telebot import types
from flask import Flask
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

@app.route('/')
def home():
    return "Lucifer Bot Live - Candlestick"

def get_spot_tickers():
    try:
        r = requests.get("https://api.bitget.com/api/v2/spot/market/tickers", timeout=15).json()
        return r.get("data", []) if r.get("code")=="00000" else []
    except: return []

def get_candles(symbol, granularity="1h", limit=80):
    try:
        url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={granularity}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        data = r.get("data", [])
        return list(reversed(data))
    except: return []

def make_candle_image(symbol, granularity="1h"):
    candles = get_candles(symbol, granularity, 80)
    if len(candles) < 20:
        return None
    
    # Bitget формат: [timestamp, open, high, low, close, vol, quoteVol]
    opens = [float(c[1]) for c in candles]
    highs = [float(c[2]) for c in candles]
    lows = [float(c[3]) for c in candles]
    closes = [float(c[4]) for c in candles]
    
    # последние 50 свечей для красоты
    opens = opens[-50:]
    highs = highs[-50:]
    lows = lows[-50:]
    closes = closes[-50:]
    
    fig, ax = plt.subplots(figsize=(12,5))
    fig.patch.set_facecolor('#131722')
    ax.set_facecolor('#131722')
    
    for i in range(len(closes)):
        o = opens[i]
        h = highs[i]
        l = lows[i]
        c = closes[i]
        
        color = '#26a69a' if c >= o else '#ef5350'  # зеленый / красный как в TV
        
        # фитиль
        ax.plot([i, i], [l, h], color=color, linewidth=1, alpha=0.8)
        # тело свечи
        body_height = abs(c - o)
        body_bottom = min(o, c)
        # если свеча доджи - делаем тонкую линию
        if body_height < (h-l)*0.05:
            ax.plot([i-0.2, i+0.2], [o, o], color=color, linewidth=2)
        else:
            rect = mpatches.Rectangle((i-
