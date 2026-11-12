import os, asyncio, aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID")) if os.getenv("CHAT_ID") else 7086505670

BINANCE_API = "https://data-api.binance.vision"
BLACKLIST = ["USDC","USD1","FDUSD","BFUSD","RLUSD","XUSD","EUR","UUSD","RWUSD","USDF","USDE","TUSD","DAI","PAXG","XAUT","WBETH","BNCB","BNRB","TSLAB","GOOGLB","AVGO","SPCX","CRCLB","QQQB","U","POL","ASTER","AVGOB"]

async def get_symbols(session):
    url = f"{BINANCE_API}/api/v3/ticker/24hr"
    async with session.get(url) as r:
        data = await r.json()
        usdt = [d for d in data if d['symbol'].endswith('USDT')]
        usdt.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        top100 = [d['symbol'] for d in usdt[:100]]
        filtered = [s for s in top100 if s.replace('USDT','') not in BLACKLIST and not s.replace('USDT','').startswith("USD")]
        return filtered

async def get_data_1h(session, symbol):
    url = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=1h&limit=6"
    try:
        async with session.get(url, timeout=10) as r:
            kl = await r.json()
            if not isinstance(kl, list) or len(kl) < 6: return None
            highs = [float(k[2]) for k in kl]
            lows = [float(k[3]) for k in kl]
            closes = [float(k[4]) for k in kl]
            avg_range = sum([((h-l)/l)*100 for h,l in zip(highs,lows)])/6
            six_h_high = max(highs)
            six_h_low = min(lows)
            curr = closes[-1]
            # Buy/Sell Logic
            dist_high = (six_h_high - curr)/curr*100
            dist_low = (curr - six_h_low)/curr*100
            if dist_high < 0.15: direction = "🚀 BUY Breakout"
            elif dist_low < 0.15: direction = "🔻 SELL Breakdown"
            else: direction = "Tight"
            return avg_range, direction, six_h_high, six_h_low
    except:
        return None

async def do_scan():
    res=[]
    async with aiohttp.ClientSession() as session:
        syms = await get_symbols(session)
        for s in syms:
            d = await get_data_1h(session, s)
            if not d: continue
            avg, direction, hh, ll = d
            coin = s.replace('USDT','')
            st = "✅" if avg < 0.9 else "❌"
            res.append((coin, avg, st, direction, s))
    res.sort(key=lambda x: x[1])
    return res

def format_msg(results):
    msg = f"🔍 DELTA 20 - V18 (1H x 6)\n77 Coins | Har 15 min\n\n"
    for coin, avg, st, direction, symbol in results:
        # Coinglass Link
        cg_link = f"https://www.coinglass.com/tv/Binance_{symbol}"
        msg += f"{coin} {avg:.2f}% {st} - {direction}\n{cg_link}\n\n"
    
    tight = [r for r in results if r[2]=="✅"]
    msg += f"Total Tight: {len(tight)}/{len(results)}\n"
    if len(msg) > 3900: # Telegram limit
        msg = msg[:3900] + "\n...list long"
    return msg

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scanning V18...")
    results = await do_scan()
    await update.message.reply_text(format_msg(results), disable_web_page_preview=True)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"V18 Active - ID: {update.effective_chat.id}")

async def auto_job(context: ContextTypes.DEFAULT_TYPE):
    results = await do_scan()
    await context.bot.send_message(chat_id=CHAT_ID, text=format_msg(results), disable_web_page_preview=True)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.job_queue.run_repeating(auto_job, interval=900, first=15)
    app.run_polling()

if __name__=="__main__":
    main()
