import React from 'react';
export const metadata = { title: 'Stock Market Data Analyzer', description: 'Stock research dashboard' };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body style={{margin:0,fontFamily:'Arial, sans-serif',background:'#f5f7fb',color:'#172033'}}>{children}</body></html>;
}
