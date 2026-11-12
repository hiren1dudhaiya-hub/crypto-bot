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
        return ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","TRXUSDT","AVAXUSDT","SHIBUSDT","DOTUSDT","LINKUSDT","LTCUSDT","BCHUSDT","NEARUSDT","UNIUSDT","PEPEUSDT","APTUSDT","ETCUSDT","XLMUSDT","STXUSDT","FILUSDT","OKBUSDT","ARBUSDT","TAOUSDT","IMXUSDT","OPUSDT","INJUSDT","RNDRUSDT","AAVEUSDT","MKRUSDT","SUIUSDT","GRTUSDT","RUNEUSDT","SEIUSDT","FETUSDT","WIFUSDT","BONKUSDT","ARUSDT","LDOUSDT","STXUSDT","TIAUSDT","WLDUSDT","JUPUSDT"]

async def get_data_1h(session, symbol, sem):
    url = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=1h&limit=6"
    async with sem:
        try:
            async with session.get(url, timeout=8) as r:
                kl = await r.json()
                if not isinstance(kl, list) or len(kl) < 6: return None
                highs = [float(k[2]) for k in kl]
                lows = [float(k[3]) for k in kl]
                closes = [float(k[4]) for k in kl]
                avg_range = sum([((h-l)/l)*100 for h,l in zip(highs,lows)]) / 6
                curr = closes[-1]
                if (max(highs)-curr)/curr*100 < 0.15: direction = "🚀 BUY"
                elif (curr-min(lows))/curr*100 < 0.15: direction = "🔻 SELL"
                else: direction = "Tight"
                coin = symbol.replace('USDT','')
                st = "✅" if avg_range < 0.9 else "❌"
                return (coin, avg_range, st, direction, symbol)
        except:
            return None

async def do_scan():
    async with aiohttp.ClientSession() as session:
        syms = await get_symbols(session)
        sem = asyncio.Semaphore(20)
        tasks = [get_data_1h(session, s, sem) for s in syms]
        results = await asyncio.gather(*tasks)
        res = [r for r in results if r]
        res.sort
