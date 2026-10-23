import os, time, requests, threading
import telebot
from flask import Flask
from telebot import types

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
@app.route("/")
def home(): return "V3 ULTIMATE + BUTTONS LIVE"

# --- КЭШИ ---
margin_cache=set()
leverage_cache={}
auto_chats=set()
BLACKLIST = {"ELICEUSDT","SOXSUSDT","JCTUSDT","BTWUSDT","BOBBOBUSDT","RT1USDT","ILYUSDT"}

def load_markets():
    try:
        r=requests.get("https://api.bitget.com/api/v2/spot/public/symbols",timeout=10).json()
        if r.get("code")=="00000":
            for s in r["data"]:
                if s.get("isMarginTrade"): margin_cache.add(s["symbol"])
    except: pass
    try:
        r=requests.get("https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES",timeout=12).json()
        if r.get("code")=="00000":
            for c in r["data"]: leverage_cache[c["symbol"]]=c.get("maxLever","125")
    except: pass
load_markets()

def get_klines(symbol, prod="USDT-FUTURES"):
    try:
        url = f"https://api.bitget.com/api/v2/mix/market/candles?symbol={symbol}&productType=USDT-FUTURES&granularity=5m&limit=100" if prod!="SPOT" else f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity=5min&limit=100"
        r=requests.get(url,timeout=10).json()
        if r.get("code")=="00000":
            data=list(reversed(r["data"]))
            closes=[float(x[4]) for x in data]; lows=[float(x[3]) for x in data]; highs=[float(x[2]) for x in data]; vols=[float(x[5]) for x in data]
            return closes,lows,highs,vols
    except: pass
    return None,None,None,None

def get_tickers():
    spot={}; fut={}
    try:
        d=requests.get("https://api.bitget.com/api/v2/spot/market/tickers",timeout=10).json()["data"]
        for t in d:
            if t["symbol"].endswith("USDT") and t["symbol"] not in BLACKLIST: spot[t["symbol"]]=float(t.get("change24h",0))
    except: pass
    try:
        d=requests.get("https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES",timeout=10).json()["data"]
        for t in d:
            if t["symbol"].endswith("USDT") and t["symbol"] not in BLACKLIST: fut[t["symbol"]]=float(t.get("change24h",0))
    except: pass
    return spot,fut

def rsi_calc(closes, period=14):
    if len(closes)<period+1: return 50
    gains=0; losses=0
    for i in range(1, period+1):
        diff=closes[-i]-closes[-i-1]
        if diff>0: gains+=diff
        else: losses+=-diff
    if losses==0: return 70
    rs=gains/losses
    return 100 - (100/(1+rs))

def analyze(closes,lows,highs,vols):
    price=closes[-1]
    sup=min(lows[-20:]); res=max(highs[-20:])
    if sup < price*0.7: sup=min(closes[-20:])*0.98
    if res > price*1.5: res=max(closes[-20:])*1.02
    if res<=sup: res=price*1.05; sup=price*0.95
    range_size=res-sup
    pos=(price-sup)/range_size*100 if range_size!=0 else 50
    rsi=rsi_calc(closes)
    avg_vol=sum(vols[-20:-1])/19 if len(vols)>20 else sum(vols)/len(vols)
    vol_spike=vols[-1]/avg_vol if avg_vol else 0
