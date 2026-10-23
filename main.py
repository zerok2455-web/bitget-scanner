import os, time, requests, threading
import telebot
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
@app.route("/")
def home(): return "V3.1 LIVE"

margin_cache=set()
leverage_cache={}
auto_chats=set()
BLACKLIST={"ELICEUSDT","SOXSUSDT","JCTUSDT","BTWUSDT"}

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

def get_klines(symbol):
    try:
        url=f"https://api.bitget.com/api/v2/mix/market/candles?symbol={symbol}&productType=USDT-FUTURES&granularity=5m&limit=100"
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

def rsi_calc(closes):
    if len(closes)<15: return 50
    gains=0; losses=0
    for i in range(1,15):
        diff=closes[-i]-closes[-i-1]
        if diff>0: gains+=diff
        else: losses+=-diff
    if losses==0: return 70
    rs=gains/(losses+0.001)
    return 100-(100/(1+rs))

def analyze(closes,lows,highs,vols):
    price=closes[-1]
    sup=min(lows[-20:]); res=max(highs[-20:])
    if res<=sup: res=price*1.05; sup=price*0.95
    pos=(price-sup)/(res-sup)*100 if res!=sup else 50
    rsi=rsi_calc(closes)
    avg=sum(vols[-20:-1])/19 if len(vols)>20 else sum(vols)/len(vols)
    vol_spike=vols[-1]/avg if avg>0 else 1
    if pos>65 or rsi>68:
        signal="SHORT"; emoji="🔻"; el=price*1.002; eh=price*1.012; sl=price*1.04; t1=price*0.96; t2=price*0.92; t3=price*0.85; conf=int(55+pos*0.3)
    else:
        signal="LONG"; emoji="🚀"; el=price*0.988; eh=price*0.998; sl=price*0.96; t1=price*1.04; t2=price*1.08; t3=price*1.15; conf=int(80-pos*0.2)
    conf=max(55,min(95,conf))
    return price,sup,res,pos,rsi,vol_spike,signal,emoji,el,eh,sl,t1,t2,t3,conf

def format_msg(sym,cs,cf,a):
    price,sup,res,pos,rsi,vol,signal,emoji,el,eh,sl,t1,t2,t3,conf=a
    lev=leverage_cache.get(sym,"125")
    return f"💎 {sym}\n{emoji} {signal} {conf}% | RSI {rsi:.0f} | VOL x{vol:.1f}\nFUT +{cf:.2f}% SPOT +{cs:.2f}% | {lev}x\nЦена: {price:.6f}\n📍 ВХОД: {el:.6f}-{eh:.6f} ({signal})\n🛑 СТОП: {sl:.6f}\n🎯 {t1:.6f} | {t2:.6f} | {t3:.6f}\nS:{sup:.6f} R:{res:.6f} Поз:{pos:.0f}%"

@bot.message_handler(commands=["start","help"])
def start(m):
    bot.reply_to(m,"/scan +4% LONG/SHORT RSI\n/scan2 +2%\n/top5m ранний памп\n/futures\n/calc 100 20 4\n/auto вкл алерты\n/funding BTCUSDT")

@bot.message_handler(commands=["scan"])
def scan_cmd(m):
    bot.reply_to(m,"⏳ Сканирую V3.1...")
    spot,fut=get_tickers()
    all_syms=set(list(spot.keys())+list(fut.keys()))
    top=[(s,spot.get(s,0),fut.get(s,0),max(spot.get(s,0),fut.get(s,0))) for s in all_syms if max(spot.get(s,0),fut.get(s,0))>4]
    top=sorted(top,key=lambda x:x[3],reverse=True)[:5]
    if not top: bot.send_message(m.chat.id,"Нет пампов +4% 😴 Попробуй /scan2"); return
    for sym,cs,cf,_ in top:
        c,l,h,v=get_klines(sym)
        if not c: continue
        bot.send_message(m.chat.id, format_msg(sym,cs,cf,analyze(c,l,h,v)))
        time.sleep(0.4)

@bot.message_handler(commands=["scan2"])
def scan2_cmd(m):
    spot,fut=get_tickers()
    all_syms=set(list(spot.keys())+list(fut.keys()))
    top=[(s,spot.get(s,0),fut.get(s,0),max(spot.get(s,0),fut.get(s,0))) for s in all_syms if max(spot.get(s,0),fut.get(s,0))>2]
    top=sorted(top,key=lambda x:x[3],reverse=True)[:5]
    for sym,cs,cf,_ in top:
        c,l,h,v=get_klines(sym)
        if not c: continue
        bot.send_message(m.chat.id, format_msg(sym,cs,cf,analyze(c,l,h,v)))

@bot.message_handler(commands=["top5m"])
def top5m_cmd(m):
    bot.reply_to(m,"⏳ Топ 5м...")
    _,fut=get_tickers()
    cands=[]
    for sym in list(fut.keys())[:50]:
        c,l,h,v=get_klines(sym)
        if not c or len(c)<3: continue
        vola=abs(c[-1]-c[-2])/c[-2]*100
        if vola>0.4: cands.append((sym,vola))
    cands=sorted(cands,key=lambda x:x[1],reverse=True)[:5]
    for sym,vola in cands:
        c,l,h,v=get_klines(sym)
        if not c: continue
        bot.send_message(m.chat.id, f"⚡ {sym} +{vola:.2f}% за 5м\n"+format_msg(sym,0,fut.get(sym,0),analyze(c,l,h,v)))

@bot.message_handler(commands=["futures"])
def fut_cmd(m):
    _,fut=get_tickers()
    top=sorted([(s,v) for s,v in fut.items() if v>4],key=lambda x:x[1],reverse=True)[:6]
    if not top: bot.send_message(m.chat.id,"Нет FUT +4% 😴"); return
    for s,v in top: bot.send_message(m.chat.id, f"🔥 {s} +{v:.2f}% {leverage_cache.get(s,'125')}x")

@bot.message_handler(commands=["calc"])
def calc_cmd(m):
    try:
        _,d,l,s=m.text.split(); d=float(d); l=float(l); s=float(s)
        bot.reply_to(m,f"Деп ${d} {l}x Стоп {s}% = Риск ${d*s/100:.2f} Поз ${d*l:.0f}")
    except: bot.reply_to(m,"Пример: /calc 100 20 4")

@bot.message_handler(commands=["auto"])
def auto_cmd(m):
    if m.chat.id in auto_chats:
        auto_chats.remove(m.chat.id); bot.reply_to(m,"🔕 Авто ВЫКЛ")
    else:
        auto_chats.add(m.chat.id); bot.reply_to(m,"🔔 Авто ВКЛ каждые 15м")

@bot.message_handler(commands=["funding"])
def funding_cmd(m):
    try:
        sym=m.text.split()[1].upper()
        if not sym.endswith("USDT"): sym+="USDT"
        r=requests.get(f"https://api.bitget.com/api/v2/mix/market/current-fund-rate?symbol={sym}&productType=USDT-FUTURES",timeout=8).json()
        rate=float(r["data"][0]["fundingRate"])*100
        bot.reply_to(m,f"Фандинг {sym}: {rate:.4f}%")
    except: bot.reply_to(m,"Пример: /funding BTCUSDT")

def auto_loop():
    while True:
        time.sleep(900)
        if not auto_chats: continue
        try:
            spot,fut=get_tickers()
            top=[(s,spot.get(s,0),fut.get(s,0)) for s in set(list(spot.keys())+list(fut.keys())) if max(spot.get(s,0),fut.get(s,0))>4][:3]
            for chat_id in list(auto_chats):
                for sym,cs,cf in top:
                    c,l,h,v=get_klines(sym)
                    if not c: continue
                    if analyze(c,l,h,v)[-1]>70:
                        bot.send_message(chat_id, "🔔 АВТО-ПАМП!\n"+format_msg(sym,cs,cf,analyze(c,l,h,v)))
        except: pass

def run_bot():
    while True:
        try: bot.infinity_polling(timeout=60)
        except: time.sleep(5)

threading.Thread(target=run_bot,daemon=True).start()
threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
