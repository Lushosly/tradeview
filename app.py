import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# === PAGE CONFIGURATION ===
st.set_page_config(layout="wide", page_title="TradeView Analytics")

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fff; }
    .stMetric {
        background-color: #1e2329;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #64ffda;
    }
</style>
""", unsafe_allow_html=True)

# === SIDEBAR ===
st.sidebar.header("📊 Market Configuration")
ticker = st.sidebar.text_input("Stock Ticker", value="BPOP").upper()
days = st.sidebar.slider("Timeframe (Days)", 30, 365*5, 365)
show_sma_50 = st.sidebar.checkbox("Show 50-Day SMA", value=True)
show_sma_200 = st.sidebar.checkbox("Show 200-Day SMA", value=False)
show_vol = st.sidebar.checkbox("Show Volume", value=True)

st.title(f"📈 TradeView: {ticker}")

# === DATA FETCHING ===
@st.cache_data
def get_data(symbol, period_days):
    start_date = datetime.today() - timedelta(days=period_days)
    try:
        # Fetch data
        df = yf.download(symbol, start=start_date, end=datetime.today(), progress=False)
        
        # FIX: Flatten MultiIndex columns if they exist (Common yfinance issue)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if df.empty:
            return None
        return df
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

data = get_data(ticker, days)

if data is not None and not data.empty:
    # --- METRICS SECTION ---
    try:
        # FIX: Explicitly convert to float to prevent "Series" TypeErrors
        current_price = float(data['Close'].iloc[-1])
        prev_close = float(data['Close'].iloc[-2])
        delta = float(current_price - prev_close)
        
        # Volatility Logic
        data['Returns'] = data['Close'].pct_change()
        volatility = float(data['Returns'].std() * 100 * (252**0.5))
        
        high_val = float(data['High'].max())
        low_val = float(data['Low'].min())

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"${current_price:.2f}", f"{delta:.2f}")
        col2.metric("Annualized Volatility", f"{volatility:.2f}%")
        col3.metric("Period High", f"${high_val:.2f}")
        col4.metric("Period Low", f"${low_val:.2f}")

        # --- INTERACTIVE CHART ---
        fig = go.Figure()

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'], high=data['High'],
            low=data['Low'], close=data['Close'],
            name='Price'
        ))

        # SMA 50
        if show_sma_50:
            sma50 = data['Close'].rolling(window=50).mean()
            fig.add_trace(go.Scatter(x=data.index, y=sma50, line=dict(color='#00f5d4', width=1.5), name='50-Day SMA'))
        
        # SMA 200
        if show_sma_200:
            sma200 = data['Close'].rolling(window=200).mean()
            fig.add_trace(go.Scatter(x=data.index, y=sma200, line=dict(color='#ff0055', width=1.5), name='200-Day SMA'))

        fig.update_layout(
            title=f"{ticker} Price Action",
            yaxis_title="Price (USD)",
            template="plotly_dark",
            height=600,
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- VOLUME CHART ---
        if show_vol:
            st.subheader("Trading Volume")
            vol_fig = go.Figure(data=[go.Bar(x=data.index, y=data['Volume'], marker_color='#1e2329')])
            vol_fig.update_layout(template="plotly_dark", height=200, margin=dict(t=0, b=0))
            st.plotly_chart(vol_fig, use_container_width=True)

        # --- DATA EXPORT ---
        with st.expander("📂 View Raw Financial Data"):
            st.dataframe(data.sort_index(ascending=False))
            csv = data.to_csv().encode('utf-8')
            st.download_button("📥 Download CSV", csv, f"{ticker}_data.csv", "text/csv")

    except Exception as e:
        st.error(f"Error processing data: {e}")
        st.write("Debug info:", data.head()) # Show data if error happens

else:
    st.error(f"❌ Could not load data for {ticker}. The ticker might be invalid or delisted.")
