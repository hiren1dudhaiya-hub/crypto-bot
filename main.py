import ccxt
import pandas as pd
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from ta.volatility import BollingerBands

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

COINS_49 = ["BTC/USDT","ETH/USDT","SOL/USDT","XRP/USDT","BNB/USDT","MATIC/USDT","DOGE/USDT","AVAX/USDT","LINK/USDT","SHIB/USDT","ADA/USDT","DOT/USDT","LTC/USDT","TRX/USDT","ETC/USDT","ATOM/USDT","NEAR/USDT","UNI/USDT","FIL/USDT","APT/USDT","ARB/USDT","OP/USDT","INJ/USDT","SUI/USDT","SEI/USDT","PEPE/USDT","BONK/USDT","WIF/USDT","RNDR/USDT","FET/USDT","AGIX/USDT","GRT/USDT","AAVE/USDT","MKR/USDT","SNX/USDT","CRV/USDT","LDO/USDT","RUNE/USDT","STX/USDT","IMX/USDT","FLOW/USDT","CHZ/USDT","SAND/USDT","MANA/USDT","AXS/USDT","GALA/USDT","ENJ/USDT","CFX/USDT"]

# Binance ki jagah Bybit - US server pe block nahi hota
exchange = ccxt.bybit({'enableRateLimit': True})

def get_full_data():
    data_list = []
    errors = 0
    for symbol in COINS_49:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=30)
            df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','vol'])
            if len(df) < 20: continue
            last_6 = df.tail(6).copy()
            last_6['range'] = (last_6['high'] - last_6['low']) / last_6['low'] * 100
            is_tight = (last_6['range'] < 0.9).all()
            avg_range = last_6['range'].mean()
            
            bb = BollingerBands(close=df['close'], window=20, window_dev=2)
            lower = bb.bollinger_lband().iloc[-1]
            upper = bb.bollinger_hband().iloc[-1]
            price = df['close'].iloc[-1]
            
            bb_status = "MID"
            if price <= lower*1.005: bb_status = "LOWER"
            elif price >= upper*0.995: bb_status = "UPPER"
            
            is_super = is_tight and bb_status != "MID"
            data_list.append({
                "Coin": symbol, 
                "6C Avg%": round(avg_range,2), 
                "Tight?": "YES" if is_tight else "NO", 
                "BB": bb_status, 
                "Super?": "YES" if is_super else "NO"
            })
        except Exception as e:
            print(f"Error {symbol}: {e}")
            errors += 1
            continue
    print(f"Fetched {len(data_list)}/49, errors {errors}")
    return data_list

async def auto_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = int(CHAT_ID) if CHAT_ID else context.job.chat_id
    data = get_full_data()
    
    if not data:
        await context.bot.send_message(chat_id=chat_id, text="❌ Data fetch fail - Bybit block? Check logs")
        return

    lines, buy_sell = [], []
    for d in data:
        tight = "✅" if d["Tight?"]=="YES" else "❌"
        bb = "L" if "LOWER" in d["BB"] else "U" if "UPPER" in d["BB"] else "-"
        signal_txt = ""
        if d["Super?"]=="YES":
            if d["BB"]=="LOWER":
                signal_txt = "🔥🟢BUY"
                buy_sell.append(f"🟢 BUY {d['Coin']}")
            else:
                signal_txt = "🔥🔴SELL"
                buy_sell.append(f"🔴 SELL {d['Coin']}")
        coin_short = d["Coin"].split("/")[0]
        lines.append(f"{coin_short} {d['6C Avg%']}% {tight}{bb} {signal_txt}".strip())

    msg = ""
    if buy_sell: msg += "🚨 *SIGNALS:*\n" + "\n".join(buy_sell) + "\n\n"
    # Time IST me dikhao
    ist_time = datetime.utcnow().strftime('%H:%M')
    msg += f"📊 49 COINS - {ist_time} UTC\n" + "\n".join(lines) + "\n\n✅=Tight L=Lower U=Upper"
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Checking 49 coins...")
    await auto_job(context)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("V10 FIXED - Bybit API - Har 15 min BUY/SELL + 49 Data")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.add_handler(CommandHandler("start", start_cmd))
    # Auto job
    if CHAT_ID:
        app.job_queue.run_repeating(auto_job, interval=900, first=10)
    else:
        print("CHAT_ID not set, auto scan disabled")
        app.job_queue.run_repeating(auto_job, interval=900, first=10)
    app.run_polling()

if __name__ == "__main__":
    main()
