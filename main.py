import os, asyncio, aiohttp
from collections import deque
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8465758405:AAH_YOUR_TOKEN_HERE"
CHAT_ID = int(os.getenv("CHAT_ID") or "7086505670")
BINANCE_API = "https://data-api.binance.vision"
sent_messages = deque(maxlen=10)

DELTA_COINS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","SHIBUSDT","PEPEUSDT","AVAXUSDT","ADAUSDT","LINKUSDT","DOTUSDT","TRXUSDT","BCHUSDT","LTCUSDT","NEARUSDT","SUIUSDT","APTUSDT","ARBUSDT","OPUSDT","POLUSDT","ETCUSDT","FILUSDT","UNIUSDT","AAVEUSDT","ATOMUSDT","INJUSDT","TIAUSDT","SEIUSDT","JUPUSDT","BONKUSDT","WIFUSDT","FLOKIUSDT","FETUSDT","RENDERUSDT","ARUSDT","STXUSDT","MKRUSDT","LDOUSDT","ENAUSDT","STRKUSDT","BLURUSDT","JTOUSDT","BRETTUSDT","MEMEUSDT","ONDOUSDT"]

def calc_rsi(closes, period):
    if len(closes) <= period: return [50.0]*len(closes)
    deltas = [closes[i]-closes[i-1] for i in range(1,len(closes))]
    up = sum([d if d>0 else 0 for d in deltas[:period]])/period
    down = sum([-d if d<0 else 0 for d in deltas[:period]])/period
    if down==0: down=0.001
    rsi=[0.0]*len(closes)
    rsi[period]=100.-100./(1.+up/down)
    for i in range(period,len(deltas)):
        upval=deltas[i] if deltas[i]>0 else 0
        downval=-deltas[i] if deltas[i]<0 else 0
        up=(up*(period-1)+upval)/period
        down=(down*(period-1)+downval)/period
        if down==0: down=0.001
        rsi[i+1]=100.-100./(1.+up/down)
    return rsi

async def get_data(session, symbol, sem):
    try:
        url30=f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=30m&limit=120"
        url12=f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=12h&limit=100"
        async with sem:
            async with session.get(url30, timeout=15) as r: kl30=await r.json()
            async with session.get(url12, timeout=15) as r: kl12=await r.json()
        if not isinstance(kl30,list) or not isinstance(kl12,list): return None
        closes90,highs90,lows90=[],[],[]
        for i in range(0,len(kl30)-2,3):
            c1,c2,c3=kl30[i],kl30[i+1],kl30[i+2]
            closes90.append(float(c3[4]))
            highs90.append(max(float(c1[2]),float(c2[2]),float(c3[2])))
            lows90.append(min(float(c1[3]),float(c2[3]),float(c3[3])))
        closes12=[float(k[4]) for k in kl12]
        if len(closes90)<20 or len(closes12)<20: return None
        rsi14_90=calc_rsi(closes90,14); r14=rsi14_90[-1]; ma9=sum(rsi14_90[-9:])/9
        rsi9_12=calc_rsi(closes12,9); r9=rsi9_12[-1]; ma3=sum(rsi9_12[-3:])/3
        high_break=highs90[-1]>highs90[-2]
        low_break=lows90[-1]<lows90[-2]
        rsi90_bull=r14>ma9
        rsi12_bull=r9>ma3
        is_long=high_break and rsi90_bull and rsi12_bull
        is_short=low_break and not rsi90_bull and not rsi12_bull
        return {"coin":symbol.replace("USDT",""),"rsi90_bull":rsi90_bull,"rsi12_bull":rsi12_bull,"high_break":high_break,"low_break":low_break,"is_long":is_long,"is_short":is_short}
    except: return None

async def do_scan():
    async with aiohttp.ClientSession() as session:
        sem=asyncio.Semaphore(5)
        results=await asyncio.gather(*[get_data(session,s,sem) for s in DELTA_COINS])
        final=[r for r in results if r]
        final.sort(key=lambda x: x['coin'])
        return final

def format_msg(results):
    ist=datetime.utcnow()+timedelta(hours=5,minutes=30)
    time_str=ist.strftime("%I:%M %p - %d %b")
    msg=f"<b>{time_str}</b>\n\n"
    for r in results:
        r90="💚" if r['rsi90_bull'] else "❤️"
        r12="♥️" if r['rsi12_bull'] else "💔"
        if r['high_break']: candle="💚 HB"
        elif r['low_break']: candle="❤️ LB"
        else: candle="🤍 NO"
        if r['is_long']: signal="✅ LONG"
        elif r['is_short']: signal="✅ SHORT"
        else: signal="❌"
        msg+=f"{r['coin']} 90m RSI{r90} 12h RSI{r12} 90m Candle{candle} Signal{signal}\n"
    return msg

async def delete_old_messages(bot):
    while len(sent_messages)>2:
        old_id=sent_messages.popleft()
        try: await bot.delete_message(chat_id=CHAT_ID, message_id=old_id)
        except: pass

async def background_scan(chat_id, context):
    try:
        results=await do_scan()
        if not results: return
        txt=format_msg(results)
        sent=await context.bot.send_message(chat_id=chat_id, text=txt, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        sent_messages.append(sent.message_id)
        await delete_old_messages(context.bot)
    except Exception as e: print(e)

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scanning...")
    await background_scan(update.effective_chat.id, context)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("BOT ONLINE")

async def auto_loop(app):
    await asyncio.sleep(10)
    while True:
        try:
            await background_scan(CHAT_ID, app)
            await asyncio.sleep(300)
        except: await asyncio.sleep(30)

async def post_init(app):
    asyncio.create_task(auto_loop(app))

def main():
    app=Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start",start_cmd))
    app.add_handler(CommandHandler("scan",scan_cmd))
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__": main()
