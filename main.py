import os, time, requests, threading
import telebot
from flask import Flask
from telebot import types

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
@app.route("/")
def home(): return "V3 ULTIMATE LIVE"

# --- КЭШИ ---
margin_cache=set()
leverage_cache={}
auto_chats=set() # кто включил /auto
BLACKLIST = {"ELICEUSDT","SOXSUSDT","JCTUSDT","BTWUSDT","BOBBOBUSDT"} # шлак

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
    vol_spike=vols[-1]/avg_vol if avg_vol>0 else 1
    
    # Логика
    if pos>65 or rsi>68: # у сопротивления / перекуп = SHORT
        signal="SHORT"; emoji="🔻"
        el=price*1.002; eh=price*1.012; sl=price*1.04; t1=price*0.96; t2=price*0.92; t3=price*0.85
        conf=int(55 + pos*0.3 + (rsi-50)*0.3)
    else: # LONG
        signal="LONG"; emoji="🚀"
        el=price*0.988; eh=price*0.998; sl=price*0.96; t1=price*1.04; t2=price*1.08; t3=price*1.15
        conf=int(85 - pos*0.3 + (50-rsi)*0.2)
    conf=max(55,min(95,conf))
    return price,sup,res,pos,rsi,vol_spike,signal,emoji,el,eh,sl,t1,t2,t3,conf

def format_msg(sym, cs, cf, analysis):
    price,sup,res,pos,rsi,vol_spike,signal,emoji,el,eh,sl,t1,t2,t3,conf=analysis
    lev=leverage_cache.get(sym,"125")
    margin="💰 МАРЖА" if sym in margin_cache else "Без маржи"
    vol_text="🔥 ОБЪЕМ x{:.1f}".format(vol_spike) if vol_spike>1.8 else "Объем норм"
    rsi_text=f"RSI {rsi:.0f} {'🟢 перепродан' if rsi<35 else '🔴 перекуп' if rsi>70 else ''}"
    return f"""💎 {sym}
{emoji} {signal} {conf}% | {rsi_text}
FUT +{cf:.2f}% | SPOT +{cs:.2f}% | Плечо {lev}x
{margin} | {vol_text} | Поз: {pos:.0f}%

Цена: {price:.6f}
📍 ВХОД: {el:.6f} - {eh:.6f}
🛑 СТОП: {sl:.6f} ({abs(price-sl)/price*100:.1f}%)
🎯 Т1: {t1:.6f} | Т2: {t2:.6f} | Т3: {t3:.6f}

S: {sup:.6f} R: {res:.6f}"""

# --- КОМАНДЫ ---
@bot.message_handler(commands=["start","help"])
def start(m):
    bot.reply_to(m, """💎 V3 ULTIMATE BOT

/scan - ТОП 5 пампов +4% LONG/SHORT + RSI
/scan2 - ТОП от +2% (для ночи)
/top5m - Волатильность за 5м (ранний памп)
/top - Волатильность за 15м
/futures - Только фьючи +4%
/margin - Только маржа
/funding BTCUSDT - Фандинг
/calc 100 20 4 - Калькулятор (деп 100$, плечо 20, стоп 4%)
/auto - Вкл/Выкл авто-алерты каждые 15м
/help - это меню
""")

@bot.message_handler(commands=["scan"])
def scan_cmd(m):
    bot.reply_to(m, "⏳ V3 Сканирую +4% RSI+VOL...")
    spot,fut=get_tickers()
    all_syms=set(list(spot.keys())+list(fut.keys()))
    top=[(s,spot.get(s,0),fut.get(s,0),max(spot.get(s,0),fut.get(s,0))) for s in all_syms if max(spot.get(s,0),fut.get(s,0))>4]
    top=sorted(top,key=lambda x:x[3],reverse=True)[:5]
    if not top: bot.send_message(m.chat.id, "Нет пампов +4%. Рынок спит 😴 Попробуй /scan2 или /top5m"); return
    for sym,cs,cf,_ in top:
        c,l,h,v=get_klines(sym)
        if not c: c,l,h,v=get_klines(sym,"SPOT")
        if not c: continue
        analysis=analyze(c,l,h,v)
        kb=types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(f"{analysis[6]} {sym}", callback_data=f"sig_{sym}"))
        bot.send_message(m.chat.id, format_msg(sym,cs,cf,analysis), reply_markup=kb)
        time.sleep(0.4)

@bot.message_handler(commands=["scan2"])
def scan2_cmd(m):
    bot.reply_to(m, "⏳ Сканирую +2%...")
    spot,fut=get_tickers()
    all_syms=set(list(spot.keys())+list(fut.keys()))
    top=[(s,spot.get(s,0),fut.get(s,0),max(spot.get(s,0),fut.get(s,0))) for s in all_syms if max(spot.get(s,0),fut.get(s,0))>2]
    top=sorted(top,key=lambda x:x[3],reverse=True)[:6]
    if not top: bot.send_message(m.chat.id, "Даже +2% нет"); return
    for sym,cs,cf,_ in top:
        c,l,h,v=get_klines(sym)
        if not c: continue
        bot.send_message(m.chat.id, format_msg(sym,cs,cf,analyze(c,l,h,v)))
        time.sleep(0.3)

@bot.message_handler(commands=["top5m","top"])
def top_cmd(m):
    gran="5m" if "5m" in m.text else "15m"
    bot.reply_to(m, f"⏳ Топ волатильности за {gran}...")
    spot,fut=get_tickers()
    # считаем волатильность по 5м свечам
    cands=[]
    for sym in list(fut.keys())[:60]: # лимит 60 чтобы не забанили
        c,l,h,v=get_klines(sym)
        if not c or len(c)<3: continue
        vola=abs(c[-1]-c[-2])/c[-2]*100
        if vola>0.5: cands.append((sym,vola))
    cands=sorted(cands,key=lambda x:x[1],reverse=True)[:5]
    for sym,vola in cands:
        c,l,h,v=get_klines(sym)
        bot.send_message(m.chat.id, f"⚡ {sym} +{vola:.2f}% за {gran}\n"+format_msg(sym,spot.get(sym,0),fut.get(sym,0),analyze(c,l,h,v)))
        time.sleep(0.4)

@bot.message_handler(commands=["futures"])
def fut_cmd(m):
    spot,fut=get_tickers()
    pumps=[(s,v) for s,v in fut.items() if v>4]
    top=sorted(pumps,key=lambda x:x[1],reverse=True)[:6]
    if not top: bot.send_message(m.chat.id, "Сейчас нет пампов FUT +4%. Рынок спит 😴 /scan2 для +2%"); return
    for sym,cf in top: bot.send_message(m.chat.id, f"🔥 {sym} | +{cf:.2f}% | Плечо {leverage_cache.get(sym,'125')}x")

@bot.message_handler(commands=["margin"])
def margin_cmd(m):
    spot,fut=get_tickers()
    filt=[s for s in margin_cache if max(spot.get(s,0),fut.get(s,0))>3][:6]
    for sym in filt: bot.send_message(m.chat.id, f"💰 {sym} МАРЖА | +{max(spot.get(sym,0),fut.get(sym,0)):.1f}% | {leverage_cache.get(sym,'125')}x")

@bot.message_handler(commands=["funding"])
def funding_cmd(m):
    try:
        sym=m.text.split()[1].upper()
        if not sym.endswith("USDT"): sym+="USDT"
        r=requests.get(f"https://api.bitget.com/api/v2/mix/market/current-fund-rate?symbol={sym}&productType=USDT-FUTURES",timeout=8).json()
        rate=float(r["data"][0]["fundingRate"])*100 if r.get("code")=="00000" else 0
        txt="🟢 Лонги платят шортам - скоро лонг сквиз" if rate>0.05 else "🔴 Шорты платят лонгам - скоро шорт сквиз" if rate<-0.05 else "Нейтрально"
        bot.reply_to(m, f"💸 Фандинг {sym}: {rate:.4f}%\n{txt}")
    except: bot.reply_to(m, "Пример: /funding BTCUSDT")

@bot.message_handler(commands=["calc"])
def calc_cmd(m):
    try:
        parts=m.text.split()
        dep=float(parts[1]); lev=float(parts[2]); stop_pct=float(parts[3])
        risk=dep*stop_pct/100
        pos_size=dep*lev
        liq=100/lev
        bot.reply_to(m, f"🧮 Деп: ${dep} | Плечо {lev}x | Стоп {stop_pct}%\nРиск: ${risk:.2f}\nПозиция: ${pos_size:.0f}\nЛиквидация ~{liq:.1f}%")
    except: bot.reply_to(m, "Пример: /calc 100 20 4 -> деп 100$, плечо 20х, стоп 4%")

@bot.message_handler(commands=["auto"])
def auto_cmd(m):
    if m.chat.id in auto_chats:
        auto_chats.remove(m.chat.id); bot.reply_to(m, "🔕 Авто-алерты ВЫКЛ")
    else:
        auto_chats.add(m.chat.id); bot.reply_to(m, "🔔 Авто-алерты ВКЛ! Каждые 15м буду слать пампы +4%")

def auto_loop():
    while True:
        time.sleep(900) # 15 мин
        if not auto_chats: continue
        try:
            spot,fut=get_tickers()
            top=[(s,spot.get(s,0),fut.get(s,0)) for s in set(list(spot.keys())+list(fut.keys())) if max(spot.get(s,0),fut.get(s,0))>4]
            top=sorted(top,key=lambda x:max(x[1],x[2]),reverse=True)[:3]
            for chat_id in list(auto_chats):
                for sym,cs,cf in top:
                    c,l,h,v=get_klines(sym)
                    if not c: continue
                    _,_,_,_,_,_,sig,_,_,_,_,_,_,_,conf=analyze(c,l,h,v)
                    if conf>70:
                        bot.send_message(chat_id, f"🔔 АВТО-ПАМП!\n"+format_msg(sym,cs,cf,analyze(c,l,h,v)))
                      
