import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# === PAGE CONFIGURATION ===
st.set_page_config(layout="wide", page_title="TradeView Analytics")

# CSS STYLING
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fff; }
    .metric-card {
        background-color: #1e2329;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00f5d4;
        text-align: center;
    }
    h1 { color: #00f5d4; }
</style>
""", unsafe_allow_html=True)

# === SIDEBAR CONTROLS ===
st.sidebar.header("📊 Configuration")
ticker = st.sidebar.text_input("Stock Ticker", value="AAPL").upper()
days = st.sidebar.slider("Timeframe (Days)", 30, 3650, 365)
show_sma = st.sidebar.checkbox("Show 50-Day SMA", value=True)
show_vol = st.sidebar.checkbox("Show Volume", value=True)

# === MAIN LOGIC ===
st.title(f"📈 TradeView: {ticker}")

def get_data(symbol, period_days):
    start_date = datetime.today() - timedelta(days=period_days)
    try:
        df = yf.download(symbol, start=start_date, end=datetime.today())
        if df.empty:
            return None
        return df
    except:
        return None

# Fetch Data
data = get_data(ticker, days)

if data is not None:
    # --- FINANCIAL METRICS ---
    current_price = data['Close'].iloc[-1]
    prev_close = data['Close'].iloc[-2]
    delta = current_price - prev_close
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Price", f"${current_price:.2f}", f"{delta:.2f}")
    with col2:
        # Calculate Volatility (Standard Deviation of returns)
        data['Returns'] = data['Close'].pct_change()
        volatility = data['Returns'].std() * 100
        st.metric("Volatility (Risk)", f"{volatility:.2f}%")
    with col3:
        high_52 = data['Close'].max()
        st.metric("Period High", f"${high_52:.2f}")
    with col4:
        volume = data['Volume'].iloc[-1]
        st.metric("Volume", f"{volume:,}")

    # --- INTERACTIVE CHART (Plotly) ---
    fig = go.Figure()

    # Candlestick Chart
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Market Data'
    ))

    # Technical Indicator: Moving Average (Pandas Logic)
    if show_sma:
        data['SMA50'] = data['Close'].rolling(window=50).mean()
        fig.add_trace(go.Scatter(
            x=data.index, 
            y=data['SMA50'], 
            mode='lines', 
            name='50-Day SMA',
            line=dict(color='#00f5d4', width=2)
        ))

    fig.update_layout(
        title=f"{ticker} Price Action & Technicals",
        yaxis_title="Stock Price (USD)",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- RAW DATA TABLE ---
    with st.expander("📂 View Raw Financial Data"):
        st.dataframe(data.sort_index(ascending=False))

    # --- DOWNLOAD BUTTON ---
    csv = data.to_csv().encode('utf-8')
    st.download_button(
        label="📥 Download Data CSV",
        data=csv,
        file_name=f'{ticker}_data.csv',
        mime='text/csv',
    )

else:
    st.error(f"❌ Could not find data for ticker '{ticker}'. Please check the symbol.")
