from typing import Optional
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .db import init_db, connect
from .engine import load_prices, add_indicators, store_data, backtest, check_alerts

app = FastAPI(title="Stock Market Data Analyzer", version="1.0.0",
              description="Educational stock research, indicators and strategy backtesting API.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()

class RefreshRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    start: str = "2023-01-01"
    end: Optional[str] = None
    csv_path: Optional[str] = None

class BacktestRequest(BaseModel):
    ticker: str
    fee_bps: float = 10

@app.get("/")
def root():
    return {"message":"Stock Market Data Analyzer API", "docs":"/docs"}

@app.post("/refresh")
def refresh(req: RefreshRequest):
    ticker = req.ticker.upper().strip()
    try:
        raw = load_prices(ticker, req.start, req.end, req.csv_path)
        enriched = add_indicators(raw)
        store_data(ticker, enriched)
        alerts = check_alerts(ticker, enriched.iloc[-1])
        return {"ticker":ticker, "rows":len(enriched), "latest_date":str(enriched.index[-1]),
                "latest_close":float(enriched["close"].iloc[-1]), "alerts":alerts}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/chart/{ticker}")
def chart(ticker: str, limit: int = 250):
    with connect() as c:
        rows = c.execute("""SELECT c.date,c.open,c.high,c.low,c.close,c.volume,
        i.sma20,i.sma50,i.rsi14,i.macd,i.macd_signal,i.bb_upper,i.bb_lower,i.signal
        FROM candles c LEFT JOIN indicators i ON c.ticker=i.ticker AND c.date=i.date
        WHERE c.ticker=? ORDER BY c.date DESC LIMIT ?""", (ticker.upper(),limit)).fetchall()
    return {"ticker":ticker.upper(), "data":[dict(r) for r in reversed(rows)]}

@app.post("/backtest")
def run_backtest(req: BacktestRequest):
    with connect() as c:
        rows = c.execute("""SELECT c.date,c.close,i.sma20,i.sma50 FROM candles c
        JOIN indicators i ON c.ticker=i.ticker AND c.date=i.date
        WHERE c.ticker=? ORDER BY c.date""", (req.ticker.upper(),)).fetchall()
    if not rows:
        raise HTTPException(404, "No data found. Run /refresh first.")
    df = pd.DataFrame([dict(r) for r in rows]).set_index("date")
    try:
        curve, stats = backtest(df, req.fee_bps)
        with connect() as c:
            c.execute("""INSERT INTO backtests(ticker,strategy,start_date,end_date,total_return,sharpe,max_drawdown,trades,costs)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (req.ticker.upper(),"SMA20/50",str(curve.index[0]),str(curve.index[-1]),
             stats["total_return"],stats["sharpe"],stats["max_drawdown"],stats["trades"],stats["costs"]))
        return {"ticker":req.ticker.upper(),"strategy":"SMA20/50","stats":stats,
                "equity_curve":[{"date":str(i),"equity":float(v)} for i,v in curve["equity"].items()]}
    except Exception as e:
        raise HTTPException(400,str(e))

@app.post("/portfolio/transactions")
def add_transaction(ticker: str, side: str, quantity: float, price: float):
    if side.upper() not in ("BUY","SELL") or quantity <= 0 or price <= 0:
        raise HTTPException(400,"Use BUY/SELL and positive quantity/price.")
    with connect() as c:
        c.execute("INSERT INTO portfolio_transactions(ticker,side,quantity,price) VALUES(?,?,?,?)",
                  (ticker.upper(),side.upper(),quantity,price))
    return {"status":"saved"}

@app.get("/portfolio")
def portfolio():
    with connect() as c:
        rows = c.execute("SELECT ticker,side,quantity,price FROM portfolio_transactions ORDER BY id").fetchall()
    holdings = {}
    for r in rows:
        h = holdings.setdefault(r["ticker"], {"quantity":0.0,"cost":0.0})
        q, p = r["quantity"], r["price"]
        if r["side"] == "BUY":
            h["cost"] += q*p
            h["quantity"] += q
        else:
            avg = h["cost"]/h["quantity"] if h["quantity"] else 0
            sold = min(q,h["quantity"])
            h["cost"] -= sold*avg
            h["quantity"] -= sold
    return [{"ticker":t,"quantity":round(v["quantity"],4),
             "average_cost":round(v["cost"]/v["quantity"],2) if v["quantity"] else 0}
            for t,v in holdings.items() if v["quantity"] > 0]

@app.get("/alerts")
def alerts():
    with connect() as c:
        rows = c.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 100").fetchall()
    return [dict(r) for r in rows]
