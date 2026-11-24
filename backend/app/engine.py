import numpy as np
import pandas as pd
import yfinance as yf
from .db import connect

def load_prices(ticker: str, start="2023-01-01", end=None, csv_path=None):
    if csv_path:
        df = pd.read_csv(csv_path)
        df.columns = [str(x).strip().lower().replace(" ", "_") for x in df.columns]
        if "date" not in df.columns:
            raise ValueError("CSV must contain a Date column")
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    else:
        df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
        if df.empty:
            raise ValueError(f"No data returned for {ticker}. Check ticker/date range or provide CSV.")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.to_datetime(df.index)
        df.index.name = "date"
        df.columns = [str(x).lower().replace(" ", "_") for x in df.columns]
    required = ["open", "high", "low", "close", "volume"]
    missing = [x for x in required if x not in df.columns]
    if missing:
        raise ValueError(f"Missing CSV columns: {missing}")
    if "adj_close" not in df.columns:
        df["adj_close"] = df["close"]
    df = df[["open","high","low","close","adj_close","volume"]].copy()
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"]).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df.index = df.index.strftime("%Y-%m-%d")
    return df

def add_indicators(df):
    x = df.copy()
    close = x["close"]
    x["daily_return"] = close.pct_change()
    x["sma20"] = close.rolling(20).mean()
    x["sma50"] = close.rolling(50).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    x["rsi14"] = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    x["macd"] = ema12 - ema26
    x["macd_signal"] = x["macd"].ewm(span=9, adjust=False).mean()
    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    x["bb_upper"] = mid + 2 * std
    x["bb_lower"] = mid - 2 * std
    x["signal"] = np.where((x["sma20"] > x["sma50"]) &
                           (x["sma20"].shift(1) <= x["sma50"].shift(1)), "BUY",
                    np.where((x["sma20"] < x["sma50"]) &
                           (x["sma20"].shift(1) >= x["sma50"].shift(1)), "SELL", "HOLD"))
    return x

def store_data(ticker, df):
    with connect() as c:
        c.execute("INSERT INTO symbols(ticker,name) VALUES(?,?) ON CONFLICT(ticker) DO UPDATE SET updated_at=CURRENT_TIMESTAMP", (ticker, ticker))
        for date, r in df.iterrows():
            c.execute("""INSERT INTO candles(ticker,date,open,high,low,close,adj_close,volume)
            VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(ticker,date) DO UPDATE SET
            open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,
            adj_close=excluded.adj_close,volume=excluded.volume""",
            (ticker,date,*[float(r[k]) if pd.notna(r[k]) else None for k in ["open","high","low","close","adj_close","volume"]]))
            cols = ["sma20","sma50","rsi14","macd","macd_signal","bb_upper","bb_lower"]
            vals = [float(r[k]) if pd.notna(r[k]) else None for k in cols]
            c.execute("""INSERT INTO indicators(ticker,date,sma20,sma50,rsi14,macd,macd_signal,bb_upper,bb_lower,signal)
            VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(ticker,date) DO UPDATE SET
            sma20=excluded.sma20,sma50=excluded.sma50,rsi14=excluded.rsi14,macd=excluded.macd,
            macd_signal=excluded.macd_signal,bb_upper=excluded.bb_upper,bb_lower=excluded.bb_lower,signal=excluded.signal""",
            (ticker,date,*vals,str(r["signal"])))

def backtest(df, fee_bps=10):
    x = df.dropna(subset=["sma20","sma50"]).copy()
    if len(x) < 2:
        raise ValueError("Not enough history for SMA20/50 backtest; use at least 60 trading days.")
    # Avoid look-ahead: today's signal controls the next day's position.
    x["position"] = (x["sma20"] > x["sma50"]).astype(float).shift(1).fillna(0)
    x["asset_return"] = x["close"].pct_change().fillna(0)
    x["turnover"] = x["position"].diff().abs().fillna(x["position"].abs())
    x["strategy_return"] = x["position"] * x["asset_return"] - x["turnover"] * (fee_bps / 10000)
    x["equity"] = (1 + x["strategy_return"]).cumprod()
    total = float(x["equity"].iloc[-1] - 1)
    daily_std = x["strategy_return"].std()
    sharpe = float((x["strategy_return"].mean() / daily_std) * np.sqrt(252)) if daily_std and not np.isnan(daily_std) else 0.0
    dd = x["equity"] / x["equity"].cummax() - 1
    return x, {"total_return": total, "sharpe": sharpe, "max_drawdown": float(dd.min()),
               "trades": int((x["turnover"] > 0).sum()), "costs": float((x["turnover"] * fee_bps / 10000).sum())}

def check_alerts(ticker, latest):
    fired = []
    checks = []
    if pd.notna(latest.get("rsi14")) and latest["rsi14"] >= 70:
        checks.append(("RSI_OVERBOUGHT", f"{ticker} RSI is {latest['rsi14']:.1f} (>=70)"))
    if pd.notna(latest.get("rsi14")) and latest["rsi14"] <= 30:
        checks.append(("RSI_OVERSOLD", f"{ticker} RSI is {latest['rsi14']:.1f} (<=30)"))
    if pd.notna(latest.get("close")) and pd.notna(latest.get("bb_upper")) and latest["close"] > latest["bb_upper"]:
        checks.append(("ABOVE_BOLLINGER", f"{ticker} close is above upper Bollinger Band"))
    if pd.notna(latest.get("close")) and pd.notna(latest.get("bb_lower")) and latest["close"] < latest["bb_lower"]:
        checks.append(("BELOW_BOLLINGER", f"{ticker} close is below lower Bollinger Band"))
    with connect() as c:
        for kind, message in checks:
            c.execute("INSERT INTO alerts(ticker,alert_type,message,last_fired) VALUES(?,?,?,CURRENT_TIMESTAMP)",
                      (ticker,kind,message))
            fired.append(message)
    return fired
