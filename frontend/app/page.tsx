'use client';
import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend } from 'recharts';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export default function Home() {
  const [ticker,setTicker] = useState('AAPL');
  const [data,setData] = useState<any[]>([]);
  const [status,setStatus] = useState('');
  const [stats,setStats] = useState<any>(null);
  const [busy,setBusy] = useState(false);
  async function refresh() {
    setBusy(true); setStatus('Fetching market data...');
    try {
      const r = await fetch(`${API}/refresh`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticker,start:'2023-01-01'})});
      const j = await r.json(); if(!r.ok) throw new Error(j.detail || 'Refresh failed');
      const c = await fetch(`${API}/chart/${ticker}?limit=250`); const chart = await c.json();
      setData(chart.data || []); setStatus(`Loaded ${j.rows} daily candles. Latest close: ${j.latest_close}`);
    } catch(e:any) { setStatus(e.message); } finally { setBusy(false); }
  }
  async function backtest() {
    setBusy(true);
    try {
      const r = await fetch(`${API}/backtest`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticker,fee_bps:10})});
      const j = await r.json(); if(!r.ok) throw new Error(j.detail || 'Backtest failed');
      setStats(j.stats); setStatus('Backtest completed.');
    } catch(e:any) { setStatus(e.message); } finally { setBusy(false); }
  }
  const card = {background:'#fff',padding:20,borderRadius:14,boxShadow:'0 2px 12px #1720330c'};
  const fmt = (v:number) => `${(v*100).toFixed(2)}%`;
  return <main style={{maxWidth:1150,margin:'40px auto',padding:'0 20px'}}>
    <header style={{marginBottom:25}}><div style={{color:'#2563eb',fontWeight:700}}>FINTECH • MARKET RESEARCH</div>
      <h1 style={{fontSize:32,margin:'8px 0'}}>Stock Market Data Analyzer</h1>
      <p style={{color:'#64748b'}}>Historical prices, technical indicators and strategy backtesting.</p></header>
    <section style={{...card,display:'flex',gap:12,flexWrap:'wrap',alignItems:'center',marginBottom:20}}>
      <label htmlFor="ticker">Ticker symbol</label>
      <input id="ticker" value={ticker} onChange={e=>setTicker(e.target.value.toUpperCase())} style={{padding:12,border:'1px solid #cbd5e1',borderRadius:8,width:130}} />
      <button disabled={busy} onClick={refresh} style={btn}>{busy?'Working...':'Refresh market data'}</button>
      <button disabled={busy} onClick={backtest} style={{...btn,background:'#0f766e'}}>Run SMA backtest</button>
      <span style={{color:'#64748b',fontSize:13}}>{status}</span>
    </section>
    <section style={{...card,marginBottom:20}}>
      <h2>Price and moving averages</h2>
      {data.length ? <div style={{width:'100%',height:360}}><ResponsiveContainer><LineChart data={data}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date" minTickGap={35}/><YAxis domain={['auto','auto']}/><Tooltip/><Legend/><Line type="monotone" dataKey="close" stroke="#2563eb" dot={false} name="Close"/><Line type="monotone" dataKey="sma20" stroke="#16a34a" dot={false} name="SMA 20"/><Line type="monotone" dataKey="sma50" stroke="#ea580c" dot={false} name="SMA 50"/></LineChart></ResponsiveContainer></div> : <p style={{color:'#64748b'}}>Enter a ticker and refresh to load the chart.</p>}
    </section>
    <section style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))',gap:14}}>
      {stats ? Object.entries(stats).map(([k,v])=><div key={k} style={card}><div style={{color:'#64748b',textTransform:'capitalize'}}>{k.replaceAll('_',' ')}</div><h2>{k==='total_return'||k==='max_drawdown'?fmt(Number(v)):Number(v).toFixed(3)}</h2></div>) : <div style={{...card,gridColumn:'1/-1'}}><b>Backtest results</b><p style={{color:'#64748b'}}>Run the SMA 20/50 backtest to see return, Sharpe ratio, drawdown, trades and estimated costs.</p></div>}
    </section>
    <p style={{fontSize:12,color:'#64748b',marginTop:24}}>Educational simulation only. Not investment advice. Data availability depends on the public data provider.</p>
  </main>;
}
const btn:any={padding:'12px 16px',border:0,borderRadius:8,background:'#2563eb',color:'#fff',fontWeight:700,cursor:'pointer'};
