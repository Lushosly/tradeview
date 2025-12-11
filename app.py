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
    
    /* Sidebar */
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
    
    /* Disclaimer & Info Box */
    .disclaimer {
        font-size: 0.85rem; color: #8892b0; background-color: #1e2329; 
        padding: 15px; border-radius: 5px; border-left: 4px solid #ff5f5f; margin-top: 20px;
    }
    .info-box {
        background-color: #112240; border-radius: 5px; padding: 10px; 
        border-left: 4px solid #64ffda; font-size: 0.9rem; color: #e6f1ff;
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

# === TIME LOGIC ===
def get_date_range(tf):
    today = datetime.today()
    if tf == "1M": return today - timedelta(days=30)
    if tf == "3M": return today - timedelta(days=90)
    if tf == "6M": return today - timedelta(days=180)
    if tf == "YTD": return datetime(today.year, 1, 1)
    if tf == "1Y": return today - timedelta(days=365)
    if tf == "3Y": return today - timedelta(days=365*3)
    if tf == "5Y": return today - timedelta(days=365*5)
    if tf == "Max": return datetime(1900, 1, 1)
    return today - timedelta(days=365)

start_date = get_date_range(selected_tf)

if comp_ticker:
    st.title(f"📈 TradeView: {ticker} vs {comp_ticker}")
else:
    st.title(f"📈 TradeView: {ticker}")

# === DATA ENGINE ===
@st.cache_data(ttl=3600)
def get_data(symbol, start):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(start=start, end=datetime.today())
        if df.empty: return None
        df.index = df.index.tz_localize(None)
        return df
    except:
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

df1 = get_data(ticker, start_date)
df2 = get_data(comp_ticker, start_date) if comp_ticker else None

if df1 is not None and not df1.empty:
    try:
        # Indicators
        df1['SMA_50'] = df1['Close'].rolling(window=50).mean()
        df1['RSI'] = calculate_rsi(df1)
        df1['BB_Upper'], df1['BB_Lower'] = calculate_bollinger(df1)

        # Metrics
        curr_price = float(df1['Close'].iloc[-1])
        delta = float(curr_price - df1['Close'].iloc[-2])
        pct_change = df1['Close'].pct_change()
        volatility = float(pct_change.std() * 100 * (252**0.5)) if len(df1) > 1 else 0.0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"{ticker} Price", f"${curr_price:.2f}", f"{delta:.2f}")
        c2.metric("Volatility", f"{volatility:.2f}%")
        rsi_val = float(df1['RSI'].iloc[-1]) if len(df1) > 14 else 50.0
        c3.metric("RSI (14-Day)", f"{rsi_val:.1f}")
        
        if df2 is not None:
            comp_price = float(df2['Close'].iloc[-1])
            comp_delta = float(comp_price - df2['Close'].iloc[-2])
            c4.metric(f"{comp_ticker} Price", f"${comp_price:.2f}", f"{comp_delta:.2f}")
        else:
            c4.metric("Volume", f"{int(df1['Volume'].iloc[-1]):,}")

        # === TABS ===
        tab1, tab2, tab3, tab4 = st.tabs(["📉 Price Action", "📊 Technicals", "⚔️ Comparison", "🤖 AI Forecast"])

        # TAB 1: PRICE ACTION
        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df1.index, open=df1['Open'], high=df1['High'], low=df1['Low'], close=df1['Close'], name='Price'))
            fig.add_trace(go.Scatter(x=df1.index, y=df1['SMA_50'], line=dict(color='#64ffda', width=1), name='SMA 50'))
            fig.update_layout(title=f"{ticker} Price History", yaxis_title="USD", template="plotly_dark", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # --- ANALYST INSIGHT (SMA) ---
            with st.expander("💡 Analyst Insight: Trend Analysis", expanded=True):
                sma_val = df1['SMA_50'].iloc[-1]
                trend = "BULLISH (Upward)" if curr_price > sma_val else "BEARISH (Downward)"
                color = "green" if curr_price > sma_val else "red"
                st.markdown(f"""
                The current price (**${curr_price:.2f}**) is trading **:{color}[{trend}]** relative to its 50-Day Moving Average (**${sma_val:.2f}**).
                * Generally, trading above the SMA-50 suggests short-to-medium term strength.
                * Trading below suggests potential weakness or a downtrend.
                """)

        # TAB 2: TECHNICALS
        with tab2:
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                bfig = go.Figure()
                bfig.add_trace(go.Scatter(x=df1.index, y=df1['Close'], line=dict(color='#e6f1ff', width=1), name='Price'))
                bfig.add_trace(go.Scatter(x=df1.index, y=df1['BB_Upper'], line=dict(color='rgba(100, 255, 218, 0.5)', width=1), name='Upper'))
                bfig.add_trace(go.Scatter(x=df1.index, y=df1['BB_Lower'], line=dict(color='rgba(100, 255, 218, 0.5)', width=1), name='Lower', fill='tonexty'))
                bfig.update_layout(title="Bollinger Bands", template="plotly_dark", height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(bfig, use_container_width=True)
            with col_t2:
                rfig = go.Figure()
                rfig.add_trace(go.Scatter(x=df1.index, y=df1['RSI'], line=dict(color='#fee440', width=2), name='RSI'))
                rfig.add_hline(y=70, line_dash="dash", line_color="red")
                rfig.add_hline(y=30, line_dash="dash", line_color="green")
                rfig.update_layout(title="RSI (Momentum)", template="plotly_dark", height=400, yaxis_range=[0,100], paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(rfig, use_container_width=True)

            # --- ANALYST INSIGHT (RSI) ---
            with st.expander("💡 Analyst Insight: Momentum & Volatility", expanded=True):
                # RSI Logic
                if rsi_val > 70:
                    rsi_msg = "⚠️ **Overbought (>70):** The asset may be overvalued and due for a correction."
                elif rsi_val < 30:
                    rsi_msg = "✅ **Oversold (<30):** The asset may be undervalued and due for a bounce."
                else:
                    rsi_msg = "ℹ️ **Neutral (30-70):** The asset is in a healthy trading range."
                
                # Volatility Logic
                vol_msg = "High Risk/Reward" if volatility > 30 else "Stable/Low Volatility"
                
                st.markdown(f"""
                **Relative Strength Index (RSI):** {rsi_msg}
                <br>
                **Annualized Volatility:** **{volatility:.2f}%** ({vol_msg}). Higher volatility implies larger price swings.
                """, unsafe_allow_html=True)

        # TAB 3: COMPARISON
        with tab3:
            if df2 is not None:
                df1['Return'] = (df1['Close'] / df1['Close'].iloc[0] - 1) * 100
                df2['Return'] = (df2['Close'] / df2['Close'].iloc[0] - 1) * 100
                
                comp_fig = go.Figure()
                comp_fig.add_trace(go.Scatter(x=df1.index, y=df1['Return'], name=ticker, line=dict(color='#64ffda', width=2)))
                comp_fig.add_trace(go.Scatter(x=df2.index, y=df2['Return'], name=comp_ticker, line=dict(color='#ff0055', width=2)))
                comp_fig.update_layout(title=f"Cumulative Return (%)", yaxis_title="Return (%)", template="plotly_dark", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(comp_fig, use_container_width=True)
                
                # Correlation
                common = df1.index.intersection(df2.index)
                corr = df1['Close'][common].corr(df2['Close'][common])
                
                with st.expander("💡 Analyst Insight: Correlation Analysis", expanded=True):
                    corr_strength = "Strong Positive" if corr > 0.7 else "Weak/Uncorrelated" if corr > -0.5 else "Inverse"
                    st.markdown(f"""
                    **Correlation Coefficient: {corr:.2f}** ({corr_strength})
                    * **1.0:** Assets move perfectly together.
                    * **0.0:** Assets are unrelated.
                    * **-1.0:** Assets move in opposite directions (Hedge).
                    """)
            else:
                st.info("Enter a comparison ticker in the sidebar.")

        # TAB 4: AI FORECAST
        with tab4:
            st.subheader(f"AI Trend Projection: {ticker}")
            df1['Numbers'] = list(range(0, len(df1)))
            X = np.array(df1['Numbers'])
            y = np.array(df1['Close'])
            z = np.polyfit(X, y, 1)
            p = np.poly1d(z)
            
            future_days = 30
            last_x = X[-1]
            future_X = np.arange(last_x, last_x + future_days)
            future_dates = [df1.index[-1] + timedelta(days=i) for i in range(1, future_days + 1)]
            forecast_y = p(future_X)

            ffig = go.Figure()
            ffig.add_trace(go.Scatter(x=df1.index, y=df1['Close'], name='Historical', line=dict(color='#8892b0', width=1)))
            ffig.add_trace(go.Scatter(x=future_dates, y=forecast_y, name='AI Forecast', line=dict(color='#ff0055', width=3, dash='dot')))
            ffig.update_layout(template="plotly_dark", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(ffig, use_container_width=True)
            
            # Trend Logic
            slope = z[0]
            trend_msg = "UPWARD 📈" if slope > 0 else "DOWNWARD 📉"
            
            with st.expander("💡 Analyst Insight: Predictive Model", expanded=True):
                st.markdown(f"""
                Based on a Linear Regression analysis of the selected timeframe, the mathematical trend is **{trend_msg}**.
                * **Model Slope:** {slope:.4f} (Daily price change average)
                * **Projection:** The red dotted line represents the statistical trajectory if current market conditions persist.
                """)

    except Exception as e:
        st.error(f"Calculation Error: {e}")

else:
    st.warning(f"No data found for {ticker}")

# === FOOTER DISCLAIMER ===
st.markdown("---")
st.markdown("""
<div class="disclaimer">
    <strong>⚠️ LEGAL DISCLAIMER</strong><br>
    This dashboard is for <strong>educational and research purposes only</strong>. 
    The forecasts and indicators are generated by mathematical models and do not constitute financial advice. 
    Past performance is not indicative of future results. Trade at your own risk.
</div>
""", unsafe_allow_html=True)
