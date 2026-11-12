import os, asyncio, aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# --- TOKEN - Yahan apna token daal de ---
BOT_TOKEN = os.getenv("BOT_TOKEN") or "8465758405:AAH...TeraPuraTokenYahan"
CHAT_ID = int(os.getenv("CHAT_ID") or "7086505670")

BINANCE_API = "https://data-api.binance.vision"
BLACKLIST = ["USDC","USD1","FDUSD","BFUSD","RLUSD","XUSD","EUR","UUSD","RWUSD","USDF","USDE","TUSD","DAI","PAXG","XAUT","WBETH","BNCB","BNRB","TSLAB","GOOGLB","AVGO","SPCX","CRCLB","QQQB","U","POL","ASTER","AVGOB","BDRM"]

async def get_symbols(session):
    try:
        async with session.get(f"{BINANCE_API}/api/v3/ticker/24hr", timeout=15) as r:
            data = await r.json()
            usdt = [d for d in data if d['symbol'].endswith('USDT')]
            usdt.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
            top = [d['symbol'] for d in usdt[:120]]
            clean = []
            for s in top:
                coin = s.replace('USDT','')
                if coin not in BLACKLIST and not coin.startswith('USD') and len(coin) <= 10:
                    clean.append(s)
                if len(clean) >= 77: break
            return clean
    except Exception as e:
        print(f"Symbols error: {e}")
        return ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","TRXUSDT","DOGEUSDT","BNBUSDT","AVAXUSDT","LINKUSDT","ADAUSDT","LTCUSDT","BCHUSDT","SHIBUSDT","DOTUSDT","NEARUSDT","UNIUSDT","PEPEUSDT","APTUSDT","ETCUSDT","XLMUSDT","FILUSDT","ARBUSDT","TAOUSDT","IMXUSDT","OPUSDT","SUIUSDT","TIAUSDT","WIFUSDT","BONKUSDT","ARUSDT","LDOUSDT","JUPUSDT","WLDUSDT","FETUSDT","RNDRUSDT","GRTUSDT","AAVEUSDT","MKRUSDT","STXUSDT","INJUSDT","ATOMUSDT","ENAUSDT","RENDERUSDT","SEIUSDT","STRKUSDT","ONDOUSDT","FLOKIUSDT","JASMYUSDT","BRETTUSDT","POPCATUSDT","WUSDT","NOTUSDT","ORDIUSDT","1000SATSUSDT","PENDLEUSDT","PYTHUSDT","GALAUSDT","FTMUSDT","RUNEUSDT","BONKUSDT","WIFUSDT","BOMEUSDT","ZKUSDT","ZROUSDT","LISTAUSDT","MEWUSDT","IOUSDT","WUSDT"]

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
                high6 = max(highs)
                low6 = min(lows)
                if (high6-curr)/curr*100 < 0.15: direction = "🚀 BUY"
                elif (curr-low6)/curr*100 < 0.15: direction = "🔻 SELL"
                else: direction = "Tight"
                coin = symbol.replace('USDT','')
                st = "✅" if avg_range < 0.9 else "❌"
                return (coin, avg_range, st, direction, symbol)
        except: return None

async def do_scan():
    async with aiohttp.ClientSession() as session:
        symbols = await get_symbols(session)
        sem = asyncio.Semaphore(25)
        tasks = [get_data(session, s, sem) for s in symbols]
        results = await asyncio.gather(*tasks)
        final = [r for r in results if r]
        final.sort(key=lambda x: x[1])
        return final[:77]

def format_msg(results):
    tight = len([r for r in results if r[2] == "✅"])
    msg = f"🔍 <b>DELTA 20 - (1H x 6) | {len(results)} Coins</b>\n\n"
    for coin, avg, st, direction, symbol in results:
        # PERFECT LINK - kabhi 404 nahi ayega
        link = f"https://www.delta.exchange/app/futures/{symbol}"
        msg += f'<a href="{link}">{coin}</a> {avg:.2f}% {st} {direction}\n'
    msg += f"\nTotal Tight: {tight}/{len(results)} | 24x7 Auto"
    return msg

async def background_scan(chat_id, context):
    try:
        results = await do_scan()
        if not results: return
        text = format_msg(results)
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        print("Scan sent")
    except Exception as e:
        print(f"Scan error: {e}")

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning 77 coins, ek hi msg me bhejunga...")
    asyncio.create_task(background_scan(update.effective_chat.id, context))

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ Bot ONLINE 24x7\nID: {update.effective_chat.id}\n/scan = manual scan\nAuto har 15 min")

async def auto_loop(app):
    await asyncio.sleep(20)
    print("Auto loop started")
    while True:
        try:
            print("Auto scanning...")
            await background_scan(CHAT_ID, app)
        except Exception as e:
            print(f"Auto error: {e}")
        await asyncio.sleep(900)  # 15 min

def main():
    if not BOT_TOKEN or "TeraPuraToken" in BOT_TOKEN:
        print("ERROR: Token daalo pehle!")
        return
    print(f"Starting Bot... Token OK: {BOT_TOKEN[:10]}...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    async def on_startup(a): asyncio.create_task(auto_loop(a))
    app.post_init = on_startup
    app.run_polling()

if __name__ == "__main__":
    main()
