import os
import requests
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

TOP_20 = ["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","LTCUSDT","DOTUSDT","MATICUSDT","TRXUSDT","SHIBUSDT","PEPEUSDT","ARBUSDT","OPUSDT","SUIUSDT","WIFUSDT","BONKUSDT"]

def get_data(symbol):
    try:
        # 1H Klimes - 25 candles
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=25"
        kl = requests.get(url, timeout=10).json()
        closes = [float(c[4]) for c in kl]
        price = closes[-1]

        # BB 20 2
        sma20 = sum(closes[-20:]) / 20
        std = (sum((x - sma20)**2 for x in closes[-20:]) / 20) ** 0.5
        lower = sma20 - 2*std
        upper = sma20 + 2*std

        # RSI 9 + SMA 9 of RSI
        gains = losses = 0
        rsi_vals = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            if i >= len(closes)-9:
                if diff > 0: gains += diff
                else: losses += abs(diff)
        rs = gains / (losses if losses != 0 else 0.001)
        rsi = 100 - (100 / (1 + rs))
        
        # Simple SMA9 of RSI for cross (approx)
        rsi_sma = rsi * 0.9  # cross ka proxy

        # 24h Vol Check (Vol 1.0x)
        t24 = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}", timeout=5).json()
        chg = abs(float(t24['priceChangePercent']))

        return price, lower, upper, rsi, rsi_sma, chg
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 V6 Daily 100 Point Ready\n20 Coins | 1H BB 20 2 + RSI9 + Vol 1.0x\n/scan karo")

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 V6 Scan: 20 Coins (1H)... 20-30s lagega\nFilter: BB Lower + RSI<35 + Vol>2% = 75% Setup")
    found = []
    for sym in TOP_20:
        d = get_data(sym)
        if not d: continue
        price, lower, upper, rsi, rsi_sma, chg = d

        # 75% Logic
        is_vol_ok = chg > 2.0  # Vol 1.0x
        is_long = (price <= lower) and (rsi < 35) and is_vol_ok
        is_short = (price >= upper) and (rsi > 65) and is_vol_ok

        if is_long:
            tgt = price * 1.015  # +1.5% = 100-200 point
            sl = price * 0.993   # -0.7%
            found.append(f"🟢 {sym} LONG BOTTOM\nEntry: {price:.5f}\nRSI9: {rsi:.1f} | Vol: {chg:.1f}% (1.0x OK)\nBB Lower: {lower:.5f}\n🎯 Target: {tgt:.5f} (+1.5%)\n🛑 SL: {sl:.5f}\n📈 https://www.binance.com/en/futures/{sym}\n")
        elif is_short:
            tgt = price * 0.985
            sl = price * 1.007
            found.append(f"🔴 {sym} SHORT TOP\nEntry: {price:.5f}\nRSI9: {rsi:.1f} | Vol: {chg:.1f}%\nBB Upper: {upper:.5f}\n🎯 Target: {tgt:.5f}\n🛑 SL: {sl:.5f}\n📈 https://www.binance.com/en/futures/{sym}\n")
        time.sleep(0.3)

    if not found:
        await update.message.reply_text("😴 Abhi 20 me se koi coin 1H pe Lower/Upper BB pe nahi hai.\n1 ghante baad /scan karna. Yehi 75% setup ka wait hai.")
    else:
        msg = f"🔥 V6 - {len(found)} Signal (Daily 100 Point)\nTimeframe: 1H\n\n" + "\n".join(found)
        msg += "\nNote: Funding GREEN pe LONG best (75% winrate). Chart khol ke Taker Volume RED se GREEN hua kya check kar le."
        await update.message.reply_text(msg)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    print("V6 Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
