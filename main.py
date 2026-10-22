import os, time, requests, threading
import telebot
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route("/")
def home():
    return "FULL LIVE - Bitget Scanner"

margin_cache=set()
leverage_cache={}

def load_markets():
    global margin_cache, leverage_cache
    try:
        r=requests.get("https://api.bitget.com/api/v2/spot/public/symbols",timeout=10).json()
        if r.get("code")=="00000":
            for s in r["data"]:
                if s.get("isMarginTrade"):
                    margin_cache.add(s["symbol"])
    except: pass
    try:
        r=requests.get("https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES",timeout=12).json()
        if r.get("code")=="00000":
            for c in r["data"]:
                leverage_cache[c["symbol"]]=c.get("maxLever","125")
    except: pass

load_markets()

def get_klines(symbol, prod="USDT-FUTURES"):
    try:
        if prod=="SPOT":
            url=f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity=5min&limit=100"
        else:
            url=f"https://api.bitget.com/api/v2/mix/market/candles?symbol={symbol}&productType=USDT-FUTURES&granularity=5m&limit=100"
        r=requests.get(url,timeout=10).json()
        if r.get("code")=="00000":
            data=list(reversed(r["data"]))
            closes=[float(x[4]) for x in data]
            lows=[float(x[3]) for x in data]
            highs=[float(x[2]) for x in data]
            return closes, lows, highs
    except: pass
    return None,None,None

def get_tickers():
    spot={}; fut={}
    try:
        d=requests.get("https://api.bitget.com/api/v2/spot/market/tickers",timeout=10).json()["data"]
        for t in d:
            if t["symbol"].endswith("USDT"):
                spot[t["symbol"]]=float(t.get("change24h",0))
    except: pass
    try:
        d=requests.get("https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES",timeout=10).json()["data"]
        for t in d:
            if t["symbol"].endswith("USDT"):
                fut[t["symbol"]]=float(t.get("change24h",0))
    except: pass
    return spot,fut

@bot.message_handler(commands=["start"])
def start(m):
    bot.reply_to(m, "💎 FULL LIVE!\n/scan - ТОП 5 пампов\n/futures - только фьючи с плечом\n/margin - только маржа\n/signal BTCUSDT - разбор")

@bot.message_handler(commands=["scan"])
def scan_cmd(m):
    bot.reply_to(m, "⏳ Сканирую SPOT + FUTURES + MARGIN + LEVERAGE...")
    spot,fut=get_tickers()
    all_syms=set(list(spot.keys())+list(fut.keys()))
    top=[]
    for s in all_syms:
        cs=spot.get(s,0); cf=fut.get(s,0)
        if max(cs,cf) > 4:
            top.append((s,cs,cf,max(cs,cf)))
    top=sorted(top,key=lambda x:x[3],reverse=True)[:5]
    for sym,cs,cf,_ in top:
        closes,lows,highs=get_klines(sym,"USDT-FUTURES")
        if not closes:
            closes,lows,highs=get_klines(sym,"SPOT")
            if not closes: continue
        price=closes[-1]
        sup=min(lows[-20:]); res=max(highs[-20:])
        lev=leverage_cache.get(sym,"125")
        margin="💰 МАРЖА 10x" if sym in margin_cache else "Без маржи"
        text=f"""💎 {sym}
FUT +{cf:.2f}% | Плечо до {lev}x
SPOT +{cs:.2f}% | {margin}

Цена: {price:.6f}
📍 ВХОД: {sup*1.005:.6f} - {price*0.998:.6f}
🛑 СТОП: {sup*0.985:.6f}
🎯 Т1: {res*0.95:.6f}
🎯 Т2: {res:.6f}
🎯 Т3: {res*1.08:.6f}
"""
        bot.send_message(m.chat.id,text)
        time.sleep(0.5)

@bot.message_handler(commands=["futures"])
def fut_cmd(m):
    bot.reply_to(m, "⏳ Фьючи с плечом...")
    spot,fut=get_tickers()
    top=sorted(fut.items(),key=lambda x:x[1],reverse=True)[:6]
    for sym,cf in top:
        lev=leverage_cache.get(sym,"125")
        bot.send_message(m.chat.id, f"🔥 {sym} | FUT +{cf:.2f}% | ПЛЕЧО до {lev}x | SPOT +{spot.get(sym,0):.2f}%")
        time.sleep(0.3)

@bot.message_handler(commands=["margin"])
def margin_cmd(m):
    bot.reply_to(m, "⏳ Маржа 10x...")
    spot,fut=get_tickers()
    filtered=[s for s in margin_cache if spot.get(s,0)>3]
    for sym in filtered[:6]:
        lev=leverage_cache.get(sym,"125")
        bot.send_message(m.chat.id, f"💰 {sym} МАРЖА 10x | SPOT +{spot.get(sym,0):.2f}% | FUT +{fut.get(sym,0):.2f}% | Плечо {lev}x")
        time.sleep(0.3)

def run_bot():
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(e)
            time.sleep(5)

threading.Thread(target=run_bot,daemon=True).start()

if __name__=="__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)
