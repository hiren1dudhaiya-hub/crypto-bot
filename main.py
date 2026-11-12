import os, requests, pandas as pd, traceback
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from ta.volatility import BollingerBands

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

COINS_49 = ["BTC/USDT","ETH/USDT","SOL/USDT","XRP/USDT","BNB/USDT","MATIC/USDT","DOGE/USDT","AVAX/USDT","LINK/USDT","SHIB/USDT","ADA/USDT","DOT/USDT","LTC/USDT","TRX/USDT","ETC/USDT","ATOM/USDT","NEAR/USDT","UNI/USDT","FIL/USDT","APT/USDT","ARB/USDT","OP/USDT","INJ/USDT","SUI/USDT","SEI/USDT","PEPE/USDT","BONK/USDT","WIF/USDT","RNDR/USDT","FET/USDT","AGIX/USDT","GRT/USDT","AAVE/USDT","MKR/USDT","SNX/USDT","CRV/USDT","LDO/USDT","RUNE/USDT","STX/USDT","IMX/USDT","FLOW/USDT","CHZ/USDT","SAND/USDT","MANA/USDT","AXS/USDT","GALA/USDT","ENJ/USDT","CFX/USDT"]

def fetch_binance_klines(symbol): # BTC/USDT -> BTCUSDT
    try:
        binance_symbol = symbol.replace("/","") # BTCUSDT
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={binance_symbol}&interval=1h&limit=30"
        r = requests.get(url, timeout=10)
        data = r.json()
        if isinstance(data, dict) and 'code' in data: return None # invalid symbol
        # data = [[openTime, open, high, low, close, volume...], ...]
        ohlcv = []
        for k in data:
            ohlcv.append([k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])])
        return ohlcv
    except:
        return None

def get_full_data():
    data_list = []
    for symbol in COINS_49:
        ohlcv = fetch_binance_klines(symbol)
        if not ohlcv or len(ohlcv) < 20: 
            print(f"Binance fail {symbol}")
            continue
        df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','vol'])
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
        data_list.append({"Coin": symbol, "6C Avg%": round(avg_range,2), "Tight?": "YES" if is_tight else "NO", "BB": bb_status, "Super?": "YES" if is_super else "NO"})
    return data_list

async def send_scan(chat_id, context):
    try:
        data = get_full_data()
        if not data:
            await context.bot.send_message(chat_id=chat_id, text="❌ Binance API fail - logs check")
            return
        lines, buy_sell = [], []
        for d in data:
            tight = "✅" if d["Tight?"]=="YES" else "❌"
            bb = "L" if "LOWER" in d["BB"] else "U" if "UPPER" in d["BB"] else "-"
            sig = ""
            if d["Super?"]=="YES":
                if d["BB"]=="LOWER":
                    sig = "🟢BUY"; buy_sell.append(f"🟢 BUY {d['Coin']}")
                else:
                    sig = "🔴SELL"; buy_sell.append(f"🔴 SELL {d['Coin']}")
            coin_short = d["Coin"].split("/")[0]
            lines.append(f"{coin_short} {d['6C Avg%']}% {tight}{bb} {sig}".strip())
        msg = ""
        if buy_sell: msg += "🚨 *BINANCE SIGNALS:*\n" + "\n".join(buy_sell) + "\n\n"
        msg += f"📊 BINANCE 49 COINS - {datetime.now().strftime('%H:%M')} UTC ({len(data)}/49)\n" + "\n".join(lines) + "\n\n✅=Tight L=Lower U=Upper"
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ ERROR:\n{traceback.format_exc()[-800:]}")

async def auto_job(context: ContextTypes.DEFAULT_TYPE):
    if CHAT_ID: await send_scan(int(CHAT_ID), context)

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Binance se 49 coins check kar raha hu...")
    await send_scan(update.effective_chat.id, context)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("V12 BINANCE ONLY - data-api.binance.vision se - Har 15 min")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.add_handler(CommandHandler("start", start_cmd))
    if CHAT_ID:
        app.job_queue.run_repeating(auto_job, interval=900, first=10)
    app.run_polling()

if __name__ == "__main__":
    main()
