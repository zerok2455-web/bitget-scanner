import os, time, requests, threading
import telebot
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
@app.route("/")
def home(): return "FULL LIVE LONG/SHORT"

margin_cache=set()
leverage_cache={}

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
            if t["symbol"].endswith("USDT"): spot[t["symbol"]]=float(t.get("change24h",0))
    except: pass
    try:
        d=requests.get("https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES",timeout=10).json()["data"]
        for t in d:
            if t["symbol"].endswith("USDT"): fut[t["symbol"]]=float(t.get("change24h",0))
    except: pass
    return spot,fut

def analyze_signal(price, lows, highs, closes):
    # Поддержка и сопротивление за 20 свечей
    sup = min(lows[-20:])
    res = max(highs[-20:])
    # защита от глюков
    if sup < price*0.7: sup = min(closes[-20:])*0.98
    if res > price*1.5: res = max(closes[-20:])*1.02
    if res <= sup: res = price*1.05; sup = price*0.95
    
    mid = (sup + res)/2
    # Позиция цены в диапазоне 0% = у поддержки, 100% = у сопротивления
    range_size = res - sup
    if range_size == 0: pos = 50
    else: pos = (price - sup) / range_size * 100
    
    # Тренд по последним 20 закрытиям
    sma20 = sum(closes[-20:])/20
    trend_up = price > sma20
    
    if pos > 65: # близко к сопротивлению = SHORT
        signal = "SHORT"
        emoji = "🔻"
        entry_low = price*1.002
        entry_high = price*1.012
        stop = price*1.04
        t1 = price*0.96
        t2 = price*0.92
        t3 = price*0.85
        conf = int(50 + pos*0.4) # чем выше pos тем увереннее шорт
    else: # близко к поддержке = LONG
        signal = "LONG"
        emoji = "🚀"
        entry_low = price*0.988
        entry_high = price*0.998
        stop = price*0.96
        t1 = price*1.04
        t2 = price*1.08
        t3 = price*1.15
        conf = int(90 - pos*0.4) # чем ниже pos тем увереннее лонг
    
    if conf > 95: conf = 95
    if conf < 55: conf = 55
    return signal, emoji, entry_low, entry_high, stop, t1, t2, t3, sup, res, conf, pos

@bot.message_handler(commands=["start"])
def start(m):
    bot.reply_to(m, "💎 FULL LONG/SHORT LIVE!\n/scan - ТОП 5 с сигналом\n/futures - только фьючи +4%\n/margin - маржа")

@bot.message_handler(commands=["scan"])
def scan_cmd(m):
    bot.reply_to(m, "⏳ Сканирую LONG/SHORT...")
    spot,fut=get_tickers()
    all_syms=set(list(spot.keys())+list(fut.keys()))
    top=[]
    for s in all_syms:
        cs=spot.get(s,0); cf=fut.get(s,0)
        if max(cs,cf) > 4: top.append((s,cs,cf,max(cs,cf)))
    top=sorted(top,key=lambda x:x[3],reverse=True)[:5]
    
    if not top:
        bot.send_message(m.chat.id, "Сейчас нет пампов +4%. Рынок спит 😴")
        return
        
    for sym,cs,cf,_ in top:
        closes,lows,highs=get_klines(sym,"USDT-FUTURES")
        if not closes: closes,lows,highs=get_klines(sym,"SPOT")
        if not closes: continue
        price=closes[-1]
        signal, emoji, el, eh, sl, t1, t2, t3, sup, res, conf, pos = analyze_signal(price, lows, highs, closes)
        lev=leverage_cache.get(sym,"125")
        margin="💰 МАРЖА" if sym in margin_cache else "Без маржи"
        text=f"""💎 {sym}
{emoji} {signal} {conf}% | FUT +{cf:.2f}% | Плечо {lev}x
SPOT +{cs:.2f}% | {margin}
Позиция: {pos:.0f}% к сопротивлению

Цена: {price:.6f}
📍 ВХОД: {el:.6f} - {eh:.6f} ({signal})
🛑 СТОП: {sl:.6f}
🎯 Т1: {t1:.6f}
🎯 Т2: {t2:.6f}
🎯 Т3: {t3:.6f}

Поддержка: {sup:.6f}
Сопротивление: {res:.6f}
"""
        bot.send_message(m.chat.id,text)
        time.sleep(0.5)

@bot.message_handler(commands=["futures"])
def fut_cmd(m):
    bot.reply_to(m, "⏳ Ищу пампы FUT +4%...")
    spot,fut=get_tickers()
    pumps=[(s,v) for s,v in fut.items() if v>4]
    top=sorted(pumps,key=lambda x:x[1],reverse=True)[:6]
    if not top:
        bot.send_message(m.chat.id, "Сейчас нет пампов FUT +4%. Рынок спит 😴")
        return
    for sym,cf in top:
        lev=leverage_cache.get(sym,"125")
        bot.send_message(m.chat.id, f"🔥 {sym} | +{cf:.2f}% | Плечо {lev}x")
        time.sleep(0.3)

@bot.message_handler(commands=["margin"])
def margin_cmd(m):
    bot.reply_to(m, "⏳ Маржа...")
    spot,fut=get_tickers()
    filt=[s for s in margin_cache if spot.get(s,0)>3 or fut.get(s,0)>3][:6]
    if not filt:
        bot.send_message(m.chat.id, "Нет маржи с пампом")
        return
    for sym in filt:
        lev=leverage_cache.get(sym,"125")
        bot.send_message(m.chat.id, f"💰 {sym} МАРЖА | FUT +{fut.get(sym,0):.1f}% SPOT +{spot.get(sym,0):.1f}% | Плечо {lev}x")
        time.sleep(0.3)

def run_bot():
    while True:
        try: bot.infinity_polling(timeout=60)
        except: time.sleep(5)

threading.Thread(target=run_bot,daemon=True).start()
if __name__=="__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)
