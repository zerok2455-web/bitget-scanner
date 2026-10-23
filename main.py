import os, threading, time, requests
import telebot
from telebot import types
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

@app.route('/')
def home():
    return "Lucifer Bot Live - Bitget Scanner"

# ===== UTILS =====
def get_spot_tickers():
    try:
        r = requests.get("https://api.bitget.com/api/v2/spot/market/tickers", timeout=15).json()
        return r.get("data", []) if r.get("code")=="00000" else []
    except: return []

def get_futures_tickers():
    try:
        r = requests.get("https://api.bitget.com/api/v2/mix/market/tickers?productType=usdt-futures", timeout=15).json()
        return r.get("data", []) if r.get("code")=="00000" else []
    except: return []

def get_candles(symbol, granularity="1h", limit=50, is_futures=False):
    try:
        if is_futures:
            url = f"https://api.bitget.com/api/v2/mix/market/candles?symbol={symbol}&granularity={granularity}&limit={limit}&productType=usdt-futures"
        else:
            url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={granularity}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        data = r.get("data", [])
        # candles от новых к старым, перевернем
        return list(reversed(data))
    except: return []

def calc_rsi(prices, period=14):
    if len(prices) < period+1: return 50
    gains, losses = 0,0
    for i in range(1, period+1):
        diff = prices[-i] - prices[-i-1]
        if diff>0: gains+=diff
        else: losses+=-diff
    if losses==0: return 70
    rs = gains/losses
    return 100 - (100/(1+rs))

def get_vol_spike(symbol):
    try:
        candles = get_candles(symbol, "1h", 21)
        if len(candles)>5:
            vols = [float(c[5]) for c in candles]
            avg_vol = sum(vols[:-1])/len(vols[:-1]) if len(vols)>1 else 0
            vol_spike = vols
