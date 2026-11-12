import ccxt
import pandas as pd
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from ta.volatility import BollingerBands

BOT_TOKEN = os.getenv("BOT_TOKEN")

COINS_49 = ["BTC/USDT","ETH/USDT","SOL/USDT","XRP/USDT","BNB/USDT","MATIC/USDT","DOGE/USDT","AVAX/USDT","LINK/USDT","SHIB/USDT","ADA/USDT","DOT/USDT","LTC/USDT","TRX/USDT","ETC/USDT","ATOM/USDT","NEAR/USDT","UNI/USDT","FIL/USDT","APT/USDT","ARB/USDT","OP/USDT","INJ/USDT","SUI/USDT","SEI/USDT","PEPE/USDT","BONK/USDT","WIF/USDT","RNDR/USDT","FET/USDT","AGIX/USDT","GRT/USDT","AAVE/USDT","MKR/USDT","SNX/USDT","CRV/USDT","LDO/USDT","RUNE/USDT","STX/USDT","IMX/USDT","FLOW/USDT","CHZ/USDT","SAND/USDT","MANA/USDT","AXS/USDT","GALA/USDT","ENJ/USDT","CFX/USDT"]

exchange = ccxt.binance({'enableRateLimit': True})

def get_full_data():
    data_list = []
    for symbol in COINS_49:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=30)
            df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','vol'])
            last_6 = df.tail(6)
            last_6['range'] = (last_6['high'] - last_6['low']) / last_6['low'] * 100
            is_tight = (last_6['range'] < 0.9).all()
            avg_range = last_6['range'].mean()
            bb = BollingerBands(close=df['close'], window=20, window_dev=2)
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_upper'] = bb.bollinger_hband()
            price = df.iloc[-1]['close']
            bb_status = "MID"
            if price <= df.iloc[-1]['bb_lower']*1.005: bb_status = "LOWER"
            elif price >= df.iloc[-1]['bb_upper']*0.995: bb_status = "UPPER"
            is_super = is_tight and bb_status != "MID"
            data_list.append({"Coin": symbol, "6C Avg%": round(avg_range,2), "Tight?": "YES" if is_tight else "NO", "BB": bb_status, "Super?": "YES" if is_super else "NO"})
        except:
            continue
    return data_list

async def auto_job(context: ContextTypes.DEFAULT_TYPE):
    data = get_full_data()
    lines, buy_sell = [], []
    for d in data:
        tight = "✅" if d["Tight?"]=="YES" else "❌"
        bb = "L" if "LOWER" in d["BB"] else "U" if "UPPER" in d["BB"] else "-"
        signal_txt = ""
        if d["Super?"]=="YES":
            if d["BB"]=="LOWER":
                signal_txt = "🔥🟢BUY"
                buy_sell.append(f"🟢 BUY {d['Coin']} - {d['6C Avg%']}%")
            else:
                signal_txt = "🔥🔴SELL"
                buy_sell.append(f"🔴 SELL {d['Coin']} - {d['6C Avg%']}%")
        coin_short = d["Coin"].split("/")[0]
        lines.append(f"{coin_short} {d['6C Avg%']}% {tight}{bb} {signal_txt}".strip())

    msg = ""
    if buy_sell: msg += "🚨 *SIGNALS:*\n" + "\n".join(buy_sell) + "\n\n"
    msg += f"📊 49 COINS - {datetime.now().strftime('%H:%M')}\n" + "\n".join(lines) + "\n\n✅=Tight L=Lower U=Upper"
    await context.bot.send_message(chat_id=context.job.chat_id, text=msg, parse_mode="Markdown")

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Checking...")
    # Create fake job object for manual scan
    class FakeJob: chat_id = update.effective_chat.id
    context.job = FakeJob()
    await auto_job(context)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("V9 FINAL ON - Har 15 min BUY/SELL + 49 Data ek hi msg me")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.add_handler(CommandHandler("start", start_cmd))
    app.job_queue.run_repeating(auto_job, interval=900, first=10, chat_id=int(os.getenv("CHAT_ID", "0")) if os.getenv("CHAT_ID") else None)
    # Fallback if CHAT_ID not set in env for job
    if not os.getenv("CHAT_ID"):
        print("CHAT_ID env missing - auto job will need chat_id")
    app.run_polling()

if __name__ == "__main__":
    main()
