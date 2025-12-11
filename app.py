import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# === PAGE CONFIGURATION ===
st.set_page_config(layout="wide", page_title="TradeView Analytics")

# === CUSTOM CSS ===
# This forces the metrics to look like cards and hides default Streamlit clutter
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #0a192f;
    }
    
    /* Metric Cards Styling */
    div[data-testid="stMetric"] {
        background-color: #112240;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #233554;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Text Colors */
    div[data-testid="stMetricLabel"] {
        color: #8892b0 !important;
        font-size: 0.9rem;
    }
    div[data-testid="stMetricValue"] {
        color: #e6f1ff !important;
        font-family: 'monospace';
    }
    div[data-testid="stMetricDelta"] {
        font-size: 0.8rem;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #112240;
    }
</style>
""", unsafe_allow_html=True)

# === SIDEBAR ===
st.sidebar.header("📊 Configuration")
ticker = st.sidebar.text_input("Ticker Symbol", value="BPOP").upper()
days = st.sidebar.selectbox("Timeframe", [30, 90, 180, 365, 1095], index=3)
show_sma_50 = st.sidebar.checkbox("Show 50-Day SMA", value=True)
show_sma_200 = st.sidebar.checkbox("Show 200-Day SMA", value=False)
show_vol = st.sidebar.checkbox("Show Volume", value=True)

st.title(f"📈 TradeView: {ticker}")

# === DATA FETCHING ===
@st.cache_data
def get_data(symbol, period_days):
    start_date = datetime.today() - timedelta(days=period_days)
    try:
        df = yf.download(symbol, start=start_date, end=datetime.today(), progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df if not df.empty else None
    except:
        return None

data = get_data(ticker, days)

if data is not None and not data.empty:
    # --- METRICS ---
    try:
        current_price = float(data['Close'].iloc[-1])
        prev_close = float(data['Close'].iloc[-2])
        delta = float(current_price - prev_close)
        
        data['Returns'] = data['Close'].pct_change()
        volatility = float(data['Returns'].std() * 100 * (252**0.5))
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Price", f"${current_price:.2f}", f"{delta:.2f}")
        c2.metric("Volatility (Risk)", f"{volatility:.2f}%")
        c3.metric("High", f"${float(data['High'].max()):.2f}")
        c4.metric("Low", f"${float(data['Low'].min()):.2f}")

        # --- CHART ---
        fig = go.Figure()

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'], high=data['High'],
            low=data['Low'], close=data['Close'],
            name='Price'
        ))

        # SMA Lines
        if show_sma_50:
            sma50 = data['Close'].rolling(window=50).mean()
            fig.add_trace(go.Scatter(x=data.index, y=sma50, line=dict(color='#64ffda', width=1.5), name='SMA 50'))
        
        if show_sma_200:
            sma200 = data['Close'].rolling(window=200).mean()
            fig.add_trace(go.Scatter(x=data.index, y=sma200, line=dict(color='#ff5f5f', width=1.5), name='SMA 200'))

        # VISUAL FIX: Match background to app theme
        fig.update_layout(
            title=f"{ticker} Market Data",
            yaxis_title="USD",
            template="plotly_dark",
            height=600,
            paper_bgcolor='rgba(0,0,0,0)', # Transparent
            plot_bgcolor='rgba(0,0,0,0)',  # Transparent
            font=dict(color="#8892b0"),
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

        if show_vol:
            st.subheader("Trading Volume")
            vfig = go.Figure(data=[go.Bar(x=data.index, y=data['Volume'], marker_color='#233554')])
            vfig.update_layout(
                height=200, 
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=10, b=10),
                font=dict(color="#8892b0")
            )
            st.plotly_chart(vfig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")

else:
    st.error("Data not found.")
