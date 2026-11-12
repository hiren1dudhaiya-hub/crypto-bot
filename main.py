import yfinance as yf
import pandas as pd

TOP_10 = ["BTC-USD","ETH-USD","SOL-USD","XRP-USD","BNB-USD","MATIC-USD","DOGE-USD","AVAX-USD","LINK-USD","SHIB-USD"]

def scan_6_candle_tight():
    alerts = []
    for symbol in TOP_10:
        df = yf.download(symbol, period="2d", interval="1h", progress=False, auto_adjust=True)
        if len(df) < 6: continue
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df['pct'] = (df['High'] - df['Low']) / df['Low'] * 100
        
        # last 6 tight check
        if (df.tail(6)['pct'] < 0.9).all():
            alerts.append({
                "coin": symbol,
                "price": round(df.iloc[-1]['Close'], 4),
                "avg_range": round(df.tail(6)['pct'].mean(), 3)
            })
    return alerts

# Tere fadehost pe isko call kar
# result = scan_6_candle_tight()
# if result: send_telegram(result)
