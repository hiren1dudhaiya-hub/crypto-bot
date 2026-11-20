async def get_data(session, symbol, sem):
    try:
        # 90m ke liye 30m data
        url90 = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=30m&limit=120"
        # 12h ke liye direct 12h data
        url12 = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=12h&limit=100"
        
        async with sem:
            async with session.get(url90, timeout=15) as r:
                kl30 = await r.json()
            async with session.get(url12, timeout=15) as r:
                kl12 = await r.json()

        if not isinstance(kl30, list) or len(kl30) < 60: return None
        if not isinstance(kl12, list) or len(kl12) < 20: return None

        # 90m banana - tera wala logic
        closes90, highs90, lows90 = [], [], []
        for i in range(0, len(kl30)-2, 3):
            c1, c2, c3 = kl30[i], kl30[i+1], kl30[i+2]
            closes90.append(float(c3[4]))
            highs90.append(max(float(c1[2]), float(c2[2]), float(c3[2])))
            lows90.append(min(float(c1[3]), float(c2[3]), float(c3[3])))
        closes90 = np.array(closes90); highs90 = np.array(highs90); lows90 = np.array(lows90)

        # 12h ke closes
        closes12 = np.array([float(k[4]) for k in kl12])

        # 1. 90m ka 14-9
        rsi14_s = calc_rsi(closes90, 14)
        rsi14 = float(rsi14_s[-1])
        ma9 = float(np.mean(rsi14_s[-9:]))

        # 2. 12h ka 9-3
        rsi9_s = calc_rsi(closes12, 9)
        rsi9 = float(rsi9_s[-1])
        ma3 = float(np.mean(rsi9_s[-3:]))

        # 90m candle breakout
        high_break = highs90[-1] > highs90[-2]
        low_break = lows90[-1] < lows90[-2]

        coin = symbol.replace("USDT","")

        # FINAL - 90m 14-9 + 12h 9-3 + breakout
        if high_break and rsi14 > ma9 and rsi9 > ma3:
            return (coin, f"LONG R14 {rsi14:.0f} M9 {ma9:.0f} HB", symbol, True)
        if low_break and rsi14 < ma9 and rsi9 < ma3:
            return (coin, f"SHORT R14 {rsi14:.0f} M9 {ma9:.0f} LB", symbol, True)
            
        return (coin, f"{'BULL' if rsi9>ma3 else 'BEAR'} R9 {rsi9:.0f} M3 {ma3:.0f}", symbol, False)
    except Exception as e:
        print(f"Err {symbol}: {e}")
        return None
