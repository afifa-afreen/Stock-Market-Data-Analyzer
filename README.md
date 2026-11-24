# Stock Market Data Analyzer

A student-built FinTech research application that downloads historical market prices, stores daily candles in SQLite, calculates technical indicators, backtests a moving-average strategy, exposes results through FastAPI, and visualizes price trends in a Next.js dashboard.

## Features
- Yahoo Finance historical data ingestion and CSV import fallback
- SQLite tables: symbols, candles, indicators, backtests, portfolio_transactions, alerts
- SMA 20/50, RSI 14, MACD and Bollinger Bands
- SMA crossover backtest with a configurable transaction fee
- Equity curve, annualized Sharpe ratio and maximum drawdown
- Portfolio transaction ledger and average-cost position aggregation
- RSI and Bollinger Band alert records
- FastAPI documentation at `/docs`
- Next.js dashboard with ticker input, close/SMA chart and backtest metrics

## Architecture
`Yahoo Finance / CSV -> Python ingestion -> cleaning -> indicators -> SQLite -> FastAPI -> Next.js dashboard`

## Requirements
- Python 3.10+
- Node.js 18+
- Internet connection for Yahoo Finance data (CSV fallback works offline)

## Run locally (Windows PowerShell)
```powershell
cd Stock-Market-Data-Analyzer
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn app.main:app --reload --app-dir backend
```
Open http://localhost:8000/docs. In a second terminal:
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:3000.

## Quick API workflow
1. `POST /refresh` JSON: `{"ticker":"AAPL","start":"2023-01-01"}`
2. `GET /chart/AAPL`
3. `POST /backtest` JSON: `{"ticker":"AAPL","fee_bps":10}`
4. `GET /portfolio` and `GET /alerts`

## CSV format
Provide columns: `Date,Open,High,Low,Close,Volume`. `Adj Close` is optional. Use `/refresh` with a `csv_path` that is accessible to the API process.

## Docker
From the project root run `docker compose up --build`. Open the dashboard at port 3000 and API docs at port 8000.

## Refresh cadence
For a student demo, manually refresh when needed or schedule once daily after market close. Do not poll public endpoints aggressively; respect provider limits and terms. Market holidays and delayed data are normal.

## Suggested extensions
1. Add intraday and weekly timeframes with timezone-aware candle boundaries.
2. Add portfolio risk metrics: beta, VaR, correlation and sector exposure.
3. Add walk-forward validation and out-of-sample strategy evaluation.
4. Add factor research: momentum, value proxies and volatility ranking.
5. Add a broker-paper-trading mock with order lifecycle simulation (no real orders).

## Limitations
Yahoo Finance availability, symbols and historical coverage may change. Backtests are simplified, assume next-day signal execution, and do not model slippage, taxes, liquidity, corporate actions comprehensively, or live execution. Sharpe and drawdown are historical estimates, not guarantees.

## Screenshots to add
Save dashboard screenshots under `images/`: `dashboard.png`, `price_sma_chart.png`, `backtest_results.png`, plus a screenshot of `/docs`.

## Learning outcomes
Python modules, Pandas/NumPy time-series analysis, SQL/SQLite schema design, API development, backtesting concepts, React/Next.js integration, and Git/GitHub workflow.

## Disclaimer
This project is for educational purposes only. It is not financial advice, investment research for any specific person, or a recommendation to buy or sell securities.
