import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8465758405:AAH_YOUR_TOKEN_HERE"
CHAT_ID = int(os.getenv("CHAT_ID") or "7086505670")

BINANCE_API = "https://data-api.binance.vision"

DELTA_COINS = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT",
    "ADAUSDT","AVAXUSDT","LINKUSDT","BCHUSDT","LTCUSDT","XLMUSDT",
    "DOTUSDT","ATOMUSDT","ETCUSDT","FILUSDT","TRXUSDT","SHIBUSDT",
    "UNIUSDT","PEPEUSDT","ARBUSDT","OPUSDT","NEARUSDT","APTUSDT",
    "SUIUSDT","TAOUSDT","RENDERUSDT","AAVEUSDT","MKRUSDT","INJUSDT",
    "LDOUSDT","GRTUSDT","STXUSDT","IMXUSDT","HBARUSDT","VETUSDT",
    "QNTUSDT","ALGOUSDT","EGLDUSDT","FTMUSDT"
]

async def get_data(session, symbol, sem):
    url = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=1h&limit=6"
    async with sem:
        try:
            async with session.get(url, timeout=10) as r:
                kl = await r.json()
                if not isinstance(kl, list) or len(kl) < 6: return None
                highs = [float(k[2]) for k in kl]
                lows = [float(k[3]) for k in kl]
                closes = [float(k[4]) for k in kl]
                avg_range = sum([((h-l)/l)*100 for h,l in zip(highs,lows)]) / 6
                curr = closes[-1]
                high6 = max(highs); low6 = min(lows)
                if (high6-curr)/curr*100 < 0.15: direction = "🚀 BUY"
                elif (curr-low6)/curr*100 < 0.15: direction = "🔻 SELL"
                else: direction = "Tight"
                coin = symbol.replace("USDT","")
                st = "✅" if avg_range < 0.9 else "❌"
                return (coin, avg_range, st, direction, symbol)
        except: return None

async def do_scan():
    async with aiohttp.ClientSession() as session:
        sem = asyncio.Semaphore(15)
        results = await asyncio.gather(*[get_data(session, s, sem) for s in DELTA_COINS])
        final = [r for r in results if r]
        final.sort(key=lambda x: x[1])
        return final

def format_msg(results):
    tight = len([r for r in results if r[2] == "✅"])
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    time_str = ist.strftime("%d-%b %I:%M %p IST")
    msg = f"🔍 <b>DELTA 20 - (1H x 6) | {len(results)} Coins</b>\n"
    msg += f"<i>⏰ {time_str} | Auto 15 min</i>\n\n"
    for coin, avg, st, direction, symbol in results:
        link = f"https://www.delta.exchange/app/futures/trade/{coin}/{coin}USD?chart_orderbook_tab=chart"
        msg += f'<a href="{link}">{coin}</a> {avg:.2f}% {st} {direction}\n'
    msg += f"\n<b>Total Tight: {tight}/{len(results)}</b> | Live Data"
    return msg

async def background_scan(chat_id, context, is_auto=False):
    try:
        results = await do_scan()
        if results:
            txt = format_msg(results)
            if is_auto:
                txt = f"🤖 <b>AUTO SIGNAL - 15 MIN</b>\n\n" + txt
            await context.bot.send_message(chat_id=chat_id, text=txt, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        print(f"Error: {e}")

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning live data...")
    asyncio.create_task(background_scan(update.effective_chat.id, context, False))

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ BOT ONLINE 24x7\nID: {update.effective_chat.id}\n\n/scan - Manual scan\nAuto signal har 15 min me ayega")

async def auto_loop(app):
    await asyncio.sleep(10)
    # Start pe ek baar bhej de
    try: await background_scan(CHAT_ID, app, True)
    except: pass
    while True:
        await asyncio.sleep(900)  # 15 minute = 900 sec
        try:
            await background_scan(CHAT_ID, app, True)
        except Exception as e:
            print(e)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    async def on_startup(a): asyncio.create_task(auto_loop(a))
    app.post_init = on_startup
    print("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
