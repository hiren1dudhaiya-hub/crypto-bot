import os, asyncio, aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID")) if os.getenv("CHAT_ID") else 7086505670

BINANCE_API = "https://data-api.binance.vision"
BLACKLIST = ["USDC","USD1","FDUSD","BFUSD","RLUSD","XUSD","EUR","UUSD","RWUSD","USDF","USDE","TUSD","DAI","PAXG","XAUT","WBETH","BNCB","BNRB","TSLAB","GOOGLB","AVGO","SPCX","CRCLB","QQQB","U","POL","ASTER","AVGOB"]

async def get_symbols(session):
    try:
        url = f"{BINANCE_API}/api/v3/ticker/24hr"
        async with session.get(url, timeout=10) as r:
            data = await r.json()
            usdt = [d for d in data if d['symbol'].endswith('USDT')]
            usdt.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
            top100 = [d['symbol'] for d in usdt[:100]]
            filtered = [s for s in top100 if s.replace('USDT','') not in BLACKLIST and not s.replace('USDT','').startswith("USD")]
            return filtered[:77]
    except:
        return ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","TRXUSDT","AVAXUSDT","SHIBUSDT","DOTUSDT","LINKUSDT","LTCUSDT","BCHUSDT","NEARUSDT","UNIUSDT","PEPEUSDT","APTUSDT","ETCUSDT","XLMUSDT","STXUSDT","FILUSDT","OKBUSDT","ARBUSDT","TAOUSDT","IMXUSDT","OPUSDT","INJUSDT","RNDRUSDT","AAVEUSDT","MKRUSDT","SUIUSDT","GRTUSDT","RUNEUSDT","SEIUSDT","FETUSDT","WIFUSDT","BONKUSDT"]

async def get_data_1h(session, symbol, sem):
    url = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=1h&limit=6"
    async with sem:
        try:
            async with session.get(url, timeout=8) as r:
                kl = await r.json()
                if not isinstance(kl, list) or len(kl) < 6: return None
                highs = [float(k[2]) for k in kl]; lows = [float(k[3]) for k in kl]; closes = [float(k[4]) for k in kl]
                avg_range = sum([((h-l)/l)*100 for h,l in zip(highs,lows)]) / 6
                curr = closes[-1]
                if (max(highs)-curr)/curr*100 < 0.15: direction = "🚀 BUY"
                elif (curr-min(lows))/curr*100 < 0.15: direction = "🔻 SELL"
                else: direction = "Tight"
                coin = symbol.replace('USDT','')
                st = "✅" if avg_range < 0.9 else "❌"
                return (coin, avg_range, st, direction, symbol)
        except: return None

async def do_scan():
    async with aiohttp.ClientSession() as session:
        syms = await get_symbols(session)
        sem = asyncio.Semaphore(20)
        tasks = [get_data_1h(session, s, sem) for s in syms]
        results = await asyncio.gather(*tasks)
        res = [r for r in results if r]
        res.sort(key=lambda x: x[1])
        return res

def format_msg(results):
    msg = f"🔍 <b>DELTA 20 - V23 (1H x 6)</b> | {len(results)} Coins\n\n"
    for coin, avg, st, direction, symbol in results:
        delta_symbol = symbol.replace("USDT","USD")
        delta_link = f"https://www.delta.exchange/app/futures/{delta_symbol}"
        msg += f'<a href="{delta_link}">{coin}</a> {avg:.2f}% {st} {direction}\n'
    tight = len([r for r in results if r[2]=="✅"])
    msg += f"\nTotal Tight: {tight}/{len(results)}"
    return msg[:4000]

# JUGAD: Background scan
async def background_scan(chat_id, context):
    try:
        results = await do_scan()
        if results:
            await context.bot.send_message(chat_id=chat_id, text=format_msg(results), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        else:
            await context.bot.send_message(chat_id=chat_id, text="Retry - Binance busy tha")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"Scan error: {e}")

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Scan start kiya (77 coins) - 10 sec me result bhejta hu...")
    # Background me chalao, telegram timeout nahi hoga
    asyncio.create_task(background_scan(update.effective_chat.id, context))

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"V23 Active - ID: {update.effective_chat.id}\n/scan dabao - full 77 coins scan")

async def auto_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        results = await do_scan()
        if results:
            await context.bot.send_message(chat_id=CHAT_ID, text=format_msg(results), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except: pass

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.job_queue.run_repeating(auto_job, interval=900, first=20)
    app.run_polling()

if __name__ == "__main__":
    main()
