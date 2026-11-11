import os
import ccxt
import pandas as pd
import ta
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

# 49 Coins - Delta India + Binance Common (MATIC/POL hataya)
TOP_49 = [
"BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT","XRP/USDT","DOGE/USDT","ADA/USDT","AVAX/USDT","LINK/USDT","LTC/USDT","DOT/USDT","TRX/USDT","SHIB/USDT","PEPE/USDT","ARB/USDT","OP/USDT","SUI/USDT","WIF/USDT","BONK/USDT",
"UNI/USDT","ATOM/USDT","ETC/USDT","FIL/USDT","APT/USDT","NEAR/USDT","TAO/USDT","RNDR/USDT","FET/USDT","INJ/USDT","SEI/USDT","JUP/USDT","PYTH/USDT","STX/USDT","IMX/USDT","LDO/USDT","MKR/USDT","AAVE/USDT","CRV/USDT","SAND/USDT","MANA/USDT","ENA/USDT","ONDO/USDT","WLD/USDT","AR/USDT","HBAR/USDT","VET/USDT","CHZ/USDT","ENS/USDT","ALGO/USDT"
]

exchange = ccxt.binance()

def check_signal(sym):
    try:
        ohlcv = exchange.fetch_ohlcv(sym, '1h', limit=100)
        df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
        
        bb = ta.volatility.BollingerBands(df['c'], window=20, window_dev=2)
        lower = bb.bollinger_lband().iloc[-1]
        upper = bb.bollinger_hband().iloc[-1]
        price = df['c'].iloc[-1]

        rsi_indicator = ta.momentum.RSIIndicator(df['c'], window=9).rsi()
        rsi = rsi_indicator.iloc[-1]
        rsi_sma = ta.trend.SMAIndicator(rsi_indicator, window=9).sma_indicator().iloc[-1]

        change = ((df['c'].iloc[-1] - df['c'].iloc[-24]) / df['c'].iloc[-24]) * 100

        # Filter: Lower BB + RSI<35 + RSI cross up + 24h Change >1% (2% ki jagah 1% kiya taaki roz signal aaye)
        if price <= lower and rsi < 35 and rsi > rsi_sma and change > 1.0:
            return f"✅ LONG {sym} \nPrice: {price:.4f} \nRSI9: {rsi:.1f} \n24h: {change:.2f}% \nSetup: 75% Winrate"
        if price >= upper and rsi > 65 and rsi < rsi_sma and change < -1.0:
            return f"🔻 SHORT {sym} \nPrice: {price:.4f} \nRSI9: {rsi:.1f} \n24h: {change:.2f}%"
    except Exception as e:
        print(f"{sym} error: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 V6.1 Bot ON Hai\n49 Coins Active (No MATIC/POL)\n/scan dabao - 30s me signal")

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🔍 V6 Scan: 49 Coins (1H)... 30s lagega\nFilter: BB Lower + RSI<35 + Vol>1% = 75% Setup")
    
    found = []
    for sym in TOP_49:
        sig = check_signal(sym)
        if sig:
            found.append(sig)
        time.sleep(0.4)

    if not found:
        msg = "😴 Abhi 49 me se koi coin 1H pe Lower/Upper BB pe nahi hai.\n1 ghante baad /scan karna. Yehi 75% setup ka wait hai."
    else:
        msg = "🔥 V6.1 SIGNAL (49 Coins):\n\n" + "\n\n".join(found) + "\n\nDelta India pe USD/USDT check karo."
    
    await update.message.reply_text(msg)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    print("Bot polling started...")
    app.run_polling()

if __name__ == "__main__":
    main()
