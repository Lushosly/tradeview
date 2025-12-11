import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# === PAGE CONFIGURATION ===
st.set_page_config(layout="wide", page_title="TradeView Pro")

# === CSS ===
st.markdown("""
<style>
    .stApp { background-color: #0a192f; }
    
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #112240;
        padding: 15px; border-radius: 10px;
        border: 1px solid #233554; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricLabel"] { color: #8892b0 !important; }
    div[data-testid="stMetricValue"] { color: #e6f1ff !important; font-family: 'monospace'; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #112240; }
    .stTextInput>div>div>input { color: #e6f1ff; }
    
    /* Tabs */
    button[data-baseweb="tab"] { background-color: transparent !important; color: #8892b0 !important; font-weight: 600; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #64ffda !important; border-bottom: 2px solid #64ffda !important; }
    
    /* Disclaimer Box (Red Border) */
    .disclaimer {
        font-size: 0.8rem; color: #a8b2d1; background-color: #1e2329; 
        padding: 15px; border-radius: 5px; border-left: 5px solid #ff5f5f; 
        margin-top: 20px; line-height: 1.4;
    }
    
    /* Analyst Insight Box (Green Border) */
    .insight-box {
        background-color: #112240;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #64ffda;
        margin-top: 10px;
        color: #e6f1ff;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# === SIDEBAR ===
st.sidebar.header("📊 Asset Selection")
ticker = st.sidebar.text_input("Primary Ticker", value="BPOP").upper()
comp_ticker = st.sidebar.text_input("Compare Against", value="").upper()

st.sidebar.header("⚙️ Timeframe")
timeframe_options = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "Max"]
selected_tf = st.sidebar.selectbox("Range", timeframe_options, index=4)

if st.sidebar.button("🔄 Clear Cache"):
    st.cache_data.clear()

# === LEGAL DISCLAIMER (SIDEBAR) ===
st.sidebar.markdown("""
<div class="disclaimer">
    <strong>⚠️ LEGAL DISCLAIMER</strong><br><br>
    This dashboard is strictly for <strong>educational and research purposes only</strong>. 
    All data, forecasts, and technical indicators are generated algorithmically using mathematical models (Linear Regression, Moving Averages) and <strong>do not constitute financial advice</strong>, investment recommendations, or an offer to buy/sell any assets.<br><br>
    The developer assumes no liability for any financial losses. Past performance is not indicative of future results. <strong>Trade at your own risk.</strong>
</div>
""", unsafe_allow_html=True)

# === SMART DATA ENGINE ===
@st.cache_data(ttl=3600)
def get_data(symbol, tf_label):
    try:
        end_date = datetime.today()
        if tf_label == "1M": view_start = end_date - timedelta(days=30)
        elif tf_label == "3M": view_start = end_date - timedelta(days=90)
        elif tf_label == "6M": view_start = end_date - timedelta(days=180)
        elif tf_label == "YTD": view_start = datetime(end_date.year, 1, 1)
        elif tf_label == "1Y": view_start = end_date - timedelta(days=365)
        elif tf_label == "3Y": view_start = end_date - timedelta(days=365*3)
        elif tf_label == "5Y": view_start = end_date - timedelta(days=365*5)
        else: view_start = datetime(1980, 1, 1)

        math_start = view_start - timedelta(days=300)
        
        stock = yf.Ticker(symbol)
        df = stock.history(start=math_start, end=end_date)
        
        if df.empty: return None, None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.index = df.index.tz_localize(None)
        return df, view_start
    except:
        return None, None

def calculate_metrics(df):
    if len(df) < 2: return df
    
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    sma20 = df['Close'].rolling(window=20).mean()
    std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = sma20 + (std * 2)
    df['BB_Lower'] = sma20 - (std * 2)
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

# === APP LOGIC ===
if comp_ticker:
    st.title(f"📈 TradeView: {ticker} vs {comp_ticker}")
else:
    st.title(f"📈 TradeView: {ticker}")

raw_df1, view_start1 = get_data(ticker, selected_tf)
raw_df2, _ = get_data(comp_ticker, selected_tf) if comp_ticker else (None, None)

if raw_df1 is not None and not raw_df1.empty:
    try:
        df1 = calculate_metrics(raw_df1)
        view_df1 = df1[df1.index >= view_start1].copy()
        
        if view_df1.empty:
            st.warning("Data loaded, but timeframe is empty. Try a longer range.")
            st.stop()

        # Metrics
        curr_price = float(view_df1['Close'].iloc[-1])
        prev_price = float(view_df1['Close'].iloc[-2])
        delta = float(curr_price - prev_price)
        pct_change = view_df1['Close'].pct_change()
        volatility = float(pct_change.std() * 100 * (252**0.5)) if len(view_df1) > 1 else 0.0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"{ticker} Price", f"${curr_price:.2f}", f"{delta:.2f}")
        c2.metric("Volatility", f"{volatility:.2f}%")
        
        last_rsi = df1['RSI'].iloc[-1]
        rsi_txt = f"{last_rsi:.1f}" if pd.notnull(last_rsi) else "N/A"
        c3.metric("RSI (14-Day)", rsi_txt)
        
        if raw_df2 is not None:
            c4.metric(f"{comp_ticker} Price", f"${float(raw_df2['Close'].iloc[-1]):.2f}")
        else:
            c4.metric("Volume", f"{int(view_df1['Volume'].iloc[-1]):,}")

        # === TABS ===
        tab1, tab2, tab3, tab4 = st.tabs(["📉 Price Action", "📊 Technicals", "⚔️ Comparison", "🤖 AI Forecast"])

        # TAB 1: PRICE
        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=view_df1.index, open=view_df1['Open'], high=view_df1['High'], low=view_df1['Low'], close=view_df1['Close'], name='Price'))
            if not view_df1['SMA_50'].isna().all():
                fig.add_trace(go.Scatter(x=view_df1.index, y=view_df1['SMA_50'], line=dict(color='#64ffda', width=1), name='SMA 50'))
            fig.update_layout(title=f"{ticker} Price History ({selected_tf})", yaxis_title="USD", template="plotly_dark", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("💡 Analyst Insight: Trend Analysis", expanded=True):
                sma_val = df1['SMA_50'].iloc[-1]
                if pd.isna(sma_val):
                    st.markdown('<div class="insight-box">⚠️ <strong>Insufficient Data:</strong> Cannot calculate the 50-Day trend yet. Try a longer timeframe or older stock.</div>', unsafe_allow_html=True)
                else:
                    sma_val = float(sma_val)
                    if curr_price > sma_val:
                        trend_html = '<span style="color:#64ffda; font-weight:bold;">BULLISH (Upward)</span>'
                    else:
                        trend_html = '<span style="color:#ff5f5f; font-weight:bold;">BEARISH (Downward)</span>'
                    
                    st.markdown(f"""
                    <div class="insight-box">
                        The current price (<strong>${curr_price:.2f}</strong>) is trading {trend_html} relative to the 50-Day Moving Average (<strong>${sma_val:.2f}</strong>).
                        <br>• Trading above the SMA-50 suggests short-term strength.
                        <br>• Trading below suggests weakness.
                    </div>
                    """, unsafe_allow_html=True)

        # TAB 2: TECHNICALS
        with tab2:
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                bfig = go.Figure()
                bfig.add_trace(go.Scatter(x=view_df1.index, y=view_df1['Close'], line=dict(color='#e6f1ff', width=1), name='Price'))
                bfig.add_trace(go.Scatter(x=view_df1.index, y=view_df1['BB_Upper'], line=dict(color='rgba(100, 255, 218, 0.5)', width=1), name='Upper'))
                bfig.add_trace(go.Scatter(x=view_df1.index, y=view_df1['BB_Lower'], line=dict(color='rgba(100, 255, 218, 0.5)', width=1), name='Lower', fill='tonexty'))
                bfig.update_layout(title="Bollinger Bands", template="plotly_dark", height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(bfig, use_container_width=True)
            with col_t2:
                rfig = go.Figure()
                rfig.add_trace(go.Scatter(x=view_df1.index, y=view_df1['RSI'], line=dict(color='#fee440', width=2), name='RSI'))
                rfig.add_hline(y=70, line_dash="dash", line_color="red")
                rfig.add_hline(y=30, line_dash="dash", line_color="green")
                rfig.update_layout(title="RSI", template="plotly_dark", height=400, yaxis_range=[0,100], paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(rfig, use_container_width=True)

            with st.expander("💡 Analyst Insight: Momentum & Volatility", expanded=True):
                # RSI Logic
                if pd.isna(last_rsi):
                    rsi_msg = "Calculating..."
                elif last_rsi > 70: 
                    rsi_msg = "⚠️ <strong style='color:#ff5f5f'>Overbought (>70)</strong>: Potential pullback."
                elif last_rsi < 30: 
                    rsi_msg = "✅ <strong style='color:#64ffda'>Oversold (<30)</strong>: Potential bounce."
                else: 
                    rsi_msg = "ℹ️ <strong>Neutral (30-70)</strong>: Healthy trading range."
                
                # BB Logic
                bb_upper = df1['BB_Upper'].iloc[-1]
                bb_lower = df1['BB_Lower'].iloc[-1]
                bb_status = "Price is within normal bands."
                if pd.notnull(bb_upper):
                    if curr_price >= bb_upper:
                        bb_status = "⚠️ Price is touching the <strong>Upper Band</strong> (Potential breakout or pullback)."
                    elif curr_price <= bb_lower:
                        bb_status = "✅ Price is touching the <strong>Lower Band</strong> (Potential bounce)."
                
                st.markdown(f"""
                <div class="insight-box">
                    <strong>RSI Status:</strong> {rsi_msg}<br>
                    <strong>Bollinger Bands:</strong> {bb_status}
                </div>
                """, unsafe_allow_html=True)

        # TAB 3: COMPARISON
        with tab3:
            if raw_df2 is not None:
                common_idx = df1.index.intersection(raw_df2.index)
                common_idx = common_idx[common_idx >= view_start1]
                if not common_idx.empty:
                    base1 = df1.loc[common_idx[0], 'Close']
                    base2 = raw_df2.loc[common_idx[0], 'Close']
                    norm1 = (df1.loc[common_idx, 'Close'] / base1 - 1) * 100
                    norm2 = (raw_df2.loc[common_idx, 'Close'] / base2 - 1) * 100
                    
                    comp_fig = go.Figure()
                    comp_fig.add_trace(go.Scatter(x=common_idx, y=norm1, name=ticker, line=dict(color='#64ffda', width=2)))
                    comp_fig.add_trace(go.Scatter(x=common_idx, y=norm2, name=comp_ticker, line=dict(color='#ff0055', width=2)))
                    comp_fig.update_layout(title="Relative Performance (%)", template="plotly_dark", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(comp_fig, use_container_width=True)
                    
                    corr = df1.loc[common_idx, 'Close'].corr(raw_df2.loc[common_idx, 'Close'])
                    with st.expander("💡 Correlation", expanded=True):
                        st.markdown(f'<div class="insight-box"><strong>Correlation Coefficient: {corr:.2f}</strong></div>', unsafe_allow_html=True)
                else:
                    st.warning("No overlapping data found.")
            else:
                st.info("Enter comparison ticker in sidebar.")

        # TAB 4: AI FORECAST
        with tab4:
            st.subheader(f"AI Trend Projection: {ticker}")
            if len(view_df1) > 10:
                view_df1['Num'] = range(len(view_df1))
                X = np.array(view_df1['Num'])
                y = np.array(view_df1['Close'])
                z = np.polyfit(X, y, 1)
                p = np.poly1d(z)
                
                future_days = 30
                last_x = X[-1]
                future_X = np.arange(last_x, last_x + future_days)
                future_dates = [view_df1.index[-1] + timedelta(days=i) for i in range(1, future_days + 1)]
                
                ffig = go.Figure()
                ffig.add_trace(go.Scatter(x=view_df1.index, y=view_df1['Close'], name='History', line=dict(color='#8892b0', width=1)))
                ffig.add_trace(go.Scatter(x=future_dates, y=p(future_X), name='Forecast', line=dict(color='#ff0055', width=3, dash='dot')))
                ffig.update_layout(title="Linear Regression Trend", template="plotly_dark", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(ffig, use_container_width=True)
                
                with st.expander("💡 Predictive Model", expanded=True):
                    slope = z[0]
                    trend = "UPWARD" if slope > 0 else "DOWNWARD"
                    st.markdown(f'<div class="insight-box">Linear Regression indicates an <strong>{trend}</strong> trajectory.<br>Slope: {slope:.4f}</div>', unsafe_allow_html=True)
            else:
                st.warning("Not enough data points for AI prediction.")

    except Exception as e:
        st.error(f"Error: {e}")

else:
    st.warning("Data not found.")

# === FOOTER DISCLAIMER (Full Version) ===
st.markdown("---")
st.markdown("""
<div class="disclaimer">
    <strong>⚠️ LEGAL DISCLAIMER</strong><br><br>
    This dashboard is strictly for <strong>educational and research purposes only</strong>. 
    All data, forecasts, and technical indicators are generated algorithmically using mathematical models (Linear Regression, Moving Averages) and <strong>do not constitute financial advice</strong>, investment recommendations, or an offer to buy/sell any assets.<br><br>
    The developer assumes no liability for any financial losses. Past performance is not indicative of future results. <strong>Trade at your own risk.</strong>
</div>
""", unsafe_allow_html=True)
