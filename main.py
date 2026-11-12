import os
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID")) if os.getenv("CHAT_ID") and os.getenv("CHAT_ID").isdigit() else None

BINANCE_API = "https://data-api.binance.vision"
BLACKLIST = ["USDC","USD1","FDUSD","BFUSD","RLUSD","XUSD","EUR","UUSD","RWUSD","USDF","USDE","TUSD","DAI","PAXG","XAUT","WBETH","BNCB","BNRB","TSLAB","GOOGLB","AVGO","SPCX","CRCLB","QQQB","U","POL","ASTER","AVGOB"]

async def get_symbols(session):
    url = f"{BINANCE_API}/api/v3/ticker/24hr"
    async with session.get(url) as r:
        data = await r.json()
        usdt = [d for d in data if d['symbol'].endswith('USDT')]
        usdt.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        top100 = [d['symbol'] for d in usdt[:100]]
        # 77 filter
        filtered = [s for s in top100 if s.replace('USDT','') not in BLACKLIST and not s.replace('USDT','').startswith("USD")]
        return filtered # ~77

async def get_range_1h(session, symbol):
    url = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=1h&limit=6"
    try:
        async with session.get(url, timeout=10) as r:
            kl = await r.json()
            if not isinstance(kl, list) or len(kl) < 6: return None
            ranges = []
            for k in kl:
                h=float(k[2]); l=float(k[3])
                ranges.append(((h-l)/l)*100 if l!=0 else 0)
            avg = sum(ranges)/len(ranges)
            return avg
    except:
        return None

async def do_scan():
    res=[]
    async with aiohttp.ClientSession() as session:
        syms = await get_symbols(session)
        for s in syms:
            avg = await get_range_1h(session, s)
            if avg is None: continue
            coin = s.replace('USDT','')
            status = "✅" if avg < 0.9 else "❌"
            res.append((coin, avg, status))
    res.sort(key=lambda x: x[1]) # % wise low to high
    return res

def format_msg(results):
    msg = f"🔍 DELTA 20 - V17 (1H x 6)\n77 Coins - % wise Sorted\nHar 15 min\n\n"
    for coin, avg, st in results:
        msg += f"{coin} {avg:.2f}% {st}\n"
    
    tight = [f"{c} ({a:.2f}%)" for c,a,s in results if s=="✅"]
    msg += f"\nTotal Tight: {len(tight)}/{len(results)}\n"
    if tight:
        msg += f"\n🚀 SIGNAL:\n" + "\n".join(tight[:15])
    else:
        msg += "\nNo tight breakout now"
    return msg

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scanning 77 coins - 1H x 6...")
    results = await do_scan()
    await update.message.reply_text(format_msg(results))

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"V17 Active - ID: {update.effective_chat.id}")

async def auto_job(context: ContextTypes.DEFAULT_TYPE):
    if not CHAT_ID: return
    results = await do_scan()
    await context.bot.send_message(chat_id=CHAT_ID, text=format_msg(results))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    if CHAT_ID:
        app.job_queue.run_repeating(auto_job, interval=900, first=15)
    app.run_polling()

if __name__=="__main__":
    main()
