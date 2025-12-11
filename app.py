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
    
    /* Metrics Styling */
    div[data-testid="stMetric"] {
        background-color: #112240;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #233554;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricLabel"] { color: #8892b0 !important; }
    div[data-testid="stMetricValue"] { color: #e6f1ff !important; font-family: 'monospace'; }
    
    /* Input & Sidebar */
    section[data-testid="stSidebar"] { background-color: #112240; }
    .stTextInput>div>div>input { color: #e6f1ff; }
    
    /* Tabs */
    button[data-baseweb="tab"] {
        background-color: transparent !important;
        color: #8892b0 !important;
        font-weight: 600;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #64ffda !important;
        border-bottom: 2px solid #64ffda !important;
    }
</style>
""", unsafe_allow_html=True)

# === SIDEBAR ===
st.sidebar.header("📊 Market Config")
ticker = st.sidebar.text_input("Ticker Symbol", value="BPOP").upper()
days = st.sidebar.number_input("Lookback Period (Days)", 30, 3650, 365, 30)

st.title(f"📈 TradeView: {ticker}")

# === DATA ENGINE ===
@st.cache_data(ttl=3600)
def get_data(symbol, period_days):
    try:
        stock = yf.Ticker(symbol)
        start_date = datetime.today() - timedelta(days=period_days)
        df = stock.history(start=start_date, end=datetime.today())
        if df.empty: return None
        df.index = df.index.tz_localize(None)
        return df
    except Exception as e:
        return None

# === FINANCIAL LOGIC ===
def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger(data, window=20):
    sma = data['Close'].rolling(window=window).mean()
    std = data['Close'].rolling(window=window).std()
    upper = sma + (std * 2)
    lower = sma - (std * 2)
    return upper, lower

data = get_data(ticker, days)

if data is not None and not data.empty:
    try:
        # Pre-Calculate Indicators
        data['SMA_50'] = data['Close'].rolling(window=50).mean()
        data['SMA_200'] = data['Close'].rolling(window=200).mean()
        data['RSI'] = calculate_rsi(data)
        data['BB_Upper'], data['BB_Lower'] = calculate_bollinger(data)

        # --- HEADLINE METRICS ---
        current_price = float(data['Close'].iloc[-1])
        prev_close = float(data['Close'].iloc[-2])
        delta = float(current_price - prev_close)
        volatility = float(data['Close'].pct_change().std() * 100 * (252**0.5))
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Price", f"${current_price:.2f}", f"{delta:.2f}")
        c2.metric("Volatility (Risk)", f"{volatility:.2f}%")
        c3.metric("RSI (14-Day)", f"{float(data['RSI'].iloc[-1]):.1f}")
        c4.metric("Volume", f"{int(data['Volume'].iloc[-1]):,}")

        # === TABS UI ===
        tab1, tab2, tab3 = st.tabs(["📉 Price Action", "📊 Technical Analysis", "🤖 AI Forecast"])

        # TAB 1: STANDARD PRICE ACTION
        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'))
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA_50'], line=dict(color='#64ffda', width=1), name='SMA 50'))
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA_200'], line=dict(color='#ff0055', width=1), name='SMA 200'))
            
            fig.update_layout(title=f"{ticker} Price & Trends", yaxis_title="USD", template="plotly_dark", height=600, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        # TAB 2: ADVANCED TECHNICALS
        with tab2:
            st.subheader("Momentum & Volatility")
            
            # Bollinger Bands Chart
            bfig = go.Figure()
            bfig.add_trace(go.Scatter(x=data.index, y=data['Close'], line=dict(color='#e6f1ff', width=1), name='Price'))
            bfig.add_trace(go.Scatter(x=data.index, y=data['BB_Upper'], line=dict(color='rgba(100, 255, 218, 0.5)', width=1), name='Upper Band'))
            bfig.add_trace(go.Scatter(x=data.index, y=data['BB_Lower'], line=dict(color='rgba(100, 255, 218, 0.5)', width=1), name='Lower Band', fill='tonexty'))
            bfig.update_layout(title="Bollinger Bands (Volatility)", template="plotly_dark", height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(bfig, use_container_width=True)

            # RSI Chart
            rfig = go.Figure()
            rfig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='#fee440', width=2), name='RSI'))
            rfig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
            rfig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
            rfig.update_layout(title="Relative Strength Index (Momentum)", template="plotly_dark", height=300, yaxis_range=[0,100], paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(rfig, use_container_width=True)

        # TAB 3: AI FORECAST
        with tab3:
            st.subheader("Linear Regression Trend Projection")
            
            # Prepare Data for ML (Integers as X axis)
            data['Numbers'] = list(range(0, len(data)))
            X = np.array(data['Numbers'])
            y = np.array(data['Close'])
            
            # Train Model (Polynomial Fit Degree 1 = Linear Regression)
            z = np.polyfit(X, y, 1)
            p = np.poly1d(z)
            
            # Future Prediction (30 Days)
            future_days = 30
            last_x = X[-1]
            future_X = np.arange(last_x, last_x + future_days)
            future_dates = [data.index[-1] + timedelta(days=i) for i in range(1, future_days + 1)]
            forecast_y = p(future_X)

            # Plot Forecast
            ffig = go.Figure()
            ffig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Historical', line=dict(color='#8892b0', width=1)))
            ffig.add_trace(go.Scatter(x=data.index, y=p(X), name='Trend Line', line=dict(color='#64ffda', width=2, dash='dash')))
            ffig.add_trace(go.Scatter(x=future_dates, y=forecast_y, name='30-Day Forecast', line=dict(color='#ff0055', width=3)))
            
            ffig.update_layout(title=f"{ticker} AI Trend Forecast (Next 30 Days)", template="plotly_dark", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(ffig, use_container_width=True)
            
            st.info("ℹ️ This model uses NumPy Linear Regression (Ordinary Least Squares) to project the current market trend forward.")

    except Exception as e:
        st.error(f"Calculation Error: {e}")

else:
    st.warning(f"No data found for {ticker}")


