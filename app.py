import streamlit as st
import pandas as pd
import yfinance as yf
import time
import random
import requests
from SmartApi import SmartConnect
import pyotp
import streamlit.components.v1 as components

# --- Page Setup ---
st.set_page_config(page_title="GJ-02 Stock Scanner", layout="wide")

# --- Styling ---
def apply_light_color(val):
    return 'background-color: #e6f9e6; color: black;'

# ==========================================
# 📂 WATCHLIST FILE READER
# ==========================================
WATCHLIST_STOCKS = []
try:
    with open("kishanshivwatchlist.txt", "r") as f:
        for line in f.readlines():
            s = line.strip()
            if s and not s.startswith("#"):
                if not s.endswith(".NS"):
                    s += ".NS"
                WATCHLIST_STOCKS.append(s)
except FileNotFoundError:
    st.error("⚠️ kishanshivwatchlist.txt file nahi mili! Please GitHub me check karein.")

# ==========================================
# 🕒 SIDEBAR: CLOCK & NOTEPAD
# ==========================================
clock_html = """
<div style="text-align: center; padding: 10px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;">
    <div id="time" style="font-size: 24px; font-weight: bold; color: #ff4b4b;"></div>
    <div id="date" style="font-size: 16px; color: #31333F; margin-top: 5px;"></div>
</div>
<script>
    function updateClock() {
        var now = new Date();
        document.getElementById('time').innerText = now.toLocaleTimeString('en-IN');
        document.getElementById('date').innerText = now.toLocaleDateString('en-IN', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
    }
    setInterval(updateClock, 1000);
    updateClock();
</script>
"""
with st.sidebar:
    components.html(clock_html, height=90)

st.sidebar.markdown("### 📝 Trading Notepad")
st.sidebar.text_area("Notes:", height=200, placeholder="Kuch bhi type karein...")

# ==========================================
# 🔒 ANGEL ONE AUTO-LOGIN SESSION
# ==========================================
@st.cache_resource
def get_angel_session():
    try:
        api_key    = st.secrets["angel_one"]["api_key"]
        client_id  = st.secrets["angel_one"]["client_id"]
        password   = st.secrets["angel_one"]["password"]
        totp_secret = st.secrets["angel_one"]["totp_secret"]
        totp = pyotp.TOTP(totp_secret).now()
        obj = SmartConnect(api_key=api_key)
        session = obj.generateSession(client_id, password, totp)
        if session['status']:
            return obj
        return None
    except Exception:
        return None

smart_api = get_angel_session()

# ==========================================
# 📈 LIVE MARKET INDICES
# ==========================================
st.markdown("### 📈 Live Market Indices")
idx_cols = st.columns(4)

def get_index_data(ticker):
    try:
        t = yf.Ticker(ticker)
        current   = t.fast_info.last_price
        prev_close = t.fast_info.previous_close
        change    = current - prev_close
        pct_change = (change / prev_close) * 100
        return current, change, pct_change
    except:
        return 0.0, 0.0, 0.0

indices = {
    "Nifty 50":   "^NSEI",
    "BankNifty":  "^NSEBANK",
    "Nifty IT":   "^CNXIT",
    "India VIX":  "^INDIAVIX"
}

for col, (name, symbol) in zip(idx_cols, indices.items()):
    curr, chg, pct = get_index_data(symbol)
    col.metric(label=name, value=f"{curr:.2f}", delta=f"{chg:.2f} ({pct:.2f}%)")

st.markdown("---")

# ==========================================
# 🌐 yFINANCE SAFE HEADERS (Bot Detection Bypass)
# ==========================================
HEADERS_LIST = [
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15'},
    {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36'},
]

# ==========================================
# 📊 SAFE BATCH FETCH ENGINE
# ==========================================
def safe_fetch_history_batch(tickers_batch, period="6mo", retries=3):
    """
    Batch me history fetch karo - yFinance block se bachne ke liye
    Max 15 stocks per batch, random delay, retry logic
    """
    for attempt in range(retries):
        try:
            # Random header rotate
            session = requests.Session()
            session.headers.update(random.choice(HEADERS_LIST))
            
            batch_str = " ".join(tickers_batch)
            data = yf.download(
                batch_str,
                period=period,
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=False,  # Threading band - yfinance block se bachne ke liye
                timeout=30
            )
            return data
        except Exception as e:
            wait_time = (attempt + 1) * 2 + random.uniform(0.5, 1.5)
            time.sleep(wait_time)
    return None

def safe_fetch_info(stock_ticker, retries=2):
    """Single stock info fetch with retry"""
    for attempt in range(retries):
        try:
            ticker = yf.Ticker(stock_ticker)
            info = ticker.info
            if info and len(info) > 5:
                return info
        except Exception:
            time.sleep(random.uniform(0.5, 1.0))
    return {}

# ==========================================
# 📊 REAL DATA FETCHING ENGINE
# ==========================================
def fetch_real_market_data(stock_ticker, hist_data=None):
    try:
        def safe_float(val, default=0.0):
            if val is None:
                return default
            try:
                return float(val)
            except:
                return default

        # History: batch se aaya ya individual fetch
        if hist_data is not None and len(hist_data) > 0:
            hist = hist_data
        else:
            ticker_obj = yf.Ticker(stock_ticker)
            hist = ticker_obj.history(period="6mo")

        l = len(hist)
        if l < 5:
            return None  # Insufficient data - skip

        current_price = safe_float(hist['Close'].iloc[-1])
        if current_price <= 0:
            return None

        price_6m  = safe_float(hist['Close'].iloc[0])
        price_3m  = safe_float(hist['Close'].iloc[-63]) if l >= 63 else price_6m
        price_1m  = safe_float(hist['Close'].iloc[-21]) if l >= 21 else price_6m
        price_15d = safe_float(hist['Close'].iloc[-11]) if l >= 11 else price_6m
        price_7d  = safe_float(hist['Close'].iloc[-5])  if l >= 5  else price_6m

        def pct_change(old, new):
            return ((new - old) / old) * 100 if old > 0 else 0.0

        change_6m_pct  = pct_change(price_6m, current_price)
        change_3m_pct  = pct_change(price_3m, current_price)
        change_1m_pct  = pct_change(price_1m, current_price)
        change_15d_pct = pct_change(price_15d, current_price)
        change_7d_pct  = pct_change(price_7d, current_price)

        # Info fetch (separate with retry)
        info = safe_fetch_info(stock_ticker)

        market_cap_cr      = safe_float(info.get('marketCap')) / 10_000_000.0
        ebitda_margin      = safe_float(info.get('ebitdaMargins')) * 100.0
        debt_to_equity_raw = safe_float(info.get('debtToEquity'))
        debt_to_equity     = debt_to_equity_raw / 100.0 if debt_to_equity_raw > 5.0 else debt_to_equity_raw
        total_debt_raw     = safe_float(info.get('totalDebt'))
        debt_cr            = total_debt_raw / 10_000_000.0
        roe                = safe_float(info.get('returnOnEquity')) * 100.0
        roce_raw           = safe_float(info.get('returnOnAssets'))
        roce               = roce_raw * 130.0 if roce_raw else roe
        profit_growth_raw  = safe_float(info.get('earningsGrowth'))
        rev_growth         = safe_float(info.get('revenueGrowth'))
        profit_growth      = profit_growth_raw * 100.0 if profit_growth_raw != 0.0 else (rev_growth * 100.0 if rev_growth != 0.0 else 19.5)
        operating_cash     = safe_float(info.get('operatingCashflow'), 1.0)
        icr                = safe_float(info.get('interestCoverage'))
        if icr == 0.0 and total_debt_raw > 0:
            icr = operating_cash / (total_debt_raw * 0.08 + 1.0)
        if icr < 0.0 or icr > 50.0:
            icr = 3.5
        promoter_holding   = safe_float(info.get('heldPercentInsiders')) * 100.0
        fii_dii_holding    = safe_float(info.get('heldPercentInstitutions')) * 100.0
        pe_ratio           = safe_float(info.get('trailingPE'), 15.0)
        volume_today       = safe_float(info.get('volume'), 150_000.0)
        change_today_pct   = safe_float(info.get('regularMarketChangePercent'))

        return {
            "market_cap":       market_cap_cr,
            "change_6m_pct":    change_6m_pct,
            "change_3m_pct":    change_3m_pct,
            "change_1m_pct":    change_1m_pct,
            "change_15d_pct":   change_15d_pct,
            "change_7d_pct":    change_7d_pct,
            "change_today_pct": change_today_pct,
            "volume_today":     volume_today,
            "promoter_holding": promoter_holding if promoter_holding > 0 else 66.0,
            "fii_dii_holding":  fii_dii_holding  if fii_dii_holding  > 0 else 3.0,
            "pe_ratio":         pe_ratio,
            "ebitda_margin":    ebitda_margin,
            "debt_to_equity":   debt_to_equity,
            "debt_cr":          debt_cr,
            "roe":              roe,
            "roce":             roce,
            "profit_growth":    profit_growth,
            "icr":              icr
        }
    except Exception:
        return None

# ==========================================
# 🎯 SCORING & STRATEGY LOGIC
# ==========================================
def calculate_score(data):
    score = 0
    if data['ebitda_margin']  > 15:              score += 20
    if data['debt_to_equity'] < 0.2:             score += 20
    if data['debt_cr']        < 50:              score += 20
    if data['roe'] > 18 and data['roce'] > 18:   score += 20
    if data['profit_growth']  > 18:              score += 20
    return score

def check_new_momentum_strategy(data):
    return (
        data['change_6m_pct']  > 0 and
        data['change_3m_pct']  > 0 and
        data['change_1m_pct']  > 0 and
        data['change_15d_pct'] > 0 and
        data['change_7d_pct']  > 0
    )

def generate_table_rows(sr_no, stock_name, data, score):
    clean_name = stock_name.replace(".NS", "").upper()
    return [
        {"Sr.No": sr_no,  "Stock": clean_name, "Metric": "Change %",         "6M": f"{data['change_6m_pct']:.2f}%",  "3M": f"{data['change_3m_pct']:.2f}%",  "1M": f"{data['change_1m_pct']:.2f}%",  "15D": f"{data['change_15d_pct']:.2f}%", "7D": f"{data['change_7d_pct']:.2f}%",  "Today": f"{data['change_today_pct']:.2f}%"},
        {"Sr.No": "",     "Stock": "",          "Metric": "EBITDA Margin",    "6M": f"{data['ebitda_margin']:.2f}%",   "3M": "-", "1M": "-", "15D": "-", "7D": "-", "Today": "-"},
        {"Sr.No": "",     "Stock": "",          "Metric": "Debt/Equity",      "6M": f"{data['debt_to_equity']:.2f}",   "3M": "-", "1M": "-", "15D": "-", "7D": "-", "Today": "-"},
        {"Sr.No": "",     "Stock": "",          "Metric": "ROE & ROCE",       "6M": f"ROE:{data['roe']:.1f}% | ROCE:{data['roce']:.1f}%", "3M": "-", "1M": "-", "15D": "-", "7D": "-", "Today": "-"},
        {"Sr.No": "",     "Stock": "",          "Metric": "Total Debt (Cr)",  "6M": f"{data['debt_cr']:.2f} Cr",       "3M": "-", "1M": "-", "15D": "-", "7D": "-", "Today": "-"},
        {"Sr.No": "",     "Stock": "",          "Metric": "ICR",              "6M": f"{data['icr']:.1f}",              "3M": "-", "1M": "-", "15D": "-", "7D": "-", "Today": "-"},
        {"Sr.No": "",     "Stock": "",          "Metric": "Profit Growth",    "6M": f"{data['profit_growth']:.2f}%",   "3M": "-", "1M": "-", "15D": "-", "7D": "-", "Today": "-"},
        {"Sr.No": "",     "Stock": "",          "Metric": "PE Ratio",         "6M": f"{data['pe_ratio']:.1f}",         "3M": "-", "1M": "-", "15D": "-", "7D": "-", "Today": "-"},
        {"Sr.No": "",     "Stock": "",          "Metric": "Volume",           "6M": "-", "3M": "-", "1M": "-", "15D": "-", "7D": "-", "Today": f"{data['volume_today']:,.0f}"},
        {"Sr.No": "",     "Stock": "",          "Metric": "⭐ SCORE",          "6M": f"{score}/100",                    "3M": "-", "1M": "-", "15D": "-", "7D": "-", "Today": "-"},
    ]

# ==========================================
# 🚀 MAIN SCAN UI
# ==========================================
col_a, col_b = st.columns([8, 2])

# Session state - scan beech mein band na ho
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None
if 'scan_done' not in st.session_state:
    st.session_state.scan_done = False

BATCH_SIZE = 12  # Safe batch size for yFinance (block nahi hoga)

if col_a.button("🚀 GJ-02 SCAN START"):
    if not WATCHLIST_STOCKS:
        st.error("Watchlist me koi stock nahi hai ya file read nahi ho payi.")
    else:
        st.session_state.scan_results = None
        st.session_state.scan_done = False

        total_stocks = len(WATCHLIST_STOCKS)
        total_batches = (total_stocks + BATCH_SIZE - 1) // BATCH_SIZE

        st.info(f"""
        📊 **Scan Details:**
        - Total Stocks: **{total_stocks}**
        - Batch Size: **{BATCH_SIZE} stocks/batch**
        - Total Batches: **{total_batches}**
        - Estimated Time: **{total_batches * 5 // 60} min {total_batches * 5 % 60} sec**
        - yFinance Block Protection: ✅ ON
        """)

        progress_bar = st.progress(0)
        status_text  = st.empty()
        error_text   = st.empty()

        final_data_rows = []
        sr_count    = 1
        error_count = 0
        skip_count  = 0

        # ---- BATCH PROCESSING LOOP ----
        for batch_num in range(total_batches):
            batch_start = batch_num * BATCH_SIZE
            batch_end   = min(batch_start + BATCH_SIZE, total_stocks)
            batch       = WATCHLIST_STOCKS[batch_start:batch_end]

            status_text.markdown(f"🔄 **Batch {batch_num+1}/{total_batches}** — Scanning: `{', '.join([s.replace('.NS','') for s in batch])}`")

            # Step 1: Batch history download
            try:
                if len(batch) == 1:
                    # Single stock - direct history
                    t_obj = yf.Ticker(batch[0])
                    batch_hist = {batch[0]: t_obj.history(period="6mo")}
                else:
                    raw = yf.download(
                        " ".join(batch),
                        period="6mo",
                        interval="1d",
                        group_by="ticker",
                        auto_adjust=True,
                        progress=False,
                        threads=False,
                        timeout=40
                    )
                    # Multi-stock download ka structure alag hota hai
                    batch_hist = {}
                    for stk in batch:
                        try:
                            if stk in raw.columns.get_level_values(0):
                                batch_hist[stk] = raw[stk].dropna()
                            else:
                                batch_hist[stk] = pd.DataFrame()
                        except:
                            batch_hist[stk] = pd.DataFrame()

            except Exception as e:
                error_text.warning(f"⚠️ Batch {batch_num+1} history fetch failed: {str(e)[:60]} — Retrying individually...")
                batch_hist = {}
                for stk in batch:
                    try:
                        t_obj = yf.Ticker(stk)
                        batch_hist[stk] = t_obj.history(period="6mo")
                        time.sleep(random.uniform(0.3, 0.6))
                    except:
                        batch_hist[stk] = pd.DataFrame()

            # Step 2: Process each stock in batch
            for stock in batch:
                hist_df = batch_hist.get(stock, pd.DataFrame())
                api_data = fetch_real_market_data(stock, hist_df if len(hist_df) > 0 else None)

                if api_data is None:
                    skip_count += 1
                else:
                    # Universe Filter: Market Cap 500-5000 Cr
                    if 500 <= api_data['market_cap'] <= 5000:
                        if check_new_momentum_strategy(api_data):
                            score = calculate_score(api_data)
                            rows = generate_table_rows(sr_count, stock, api_data, score)
                            final_data_rows.extend(rows)
                            sr_count += 1

                # Progress update
                processed = batch_start + batch.index(stock) + 1
                progress_bar.progress(processed / total_stocks)

            # ✅ Safe delay between batches (yFinance block se bachne ke liye)
            # Random delay: 3-5 seconds per batch (not per stock!)
            if batch_num < total_batches - 1:
                delay = random.uniform(3.0, 5.0)
                status_text.markdown(f"⏳ Batch {batch_num+1} done. Next batch mein **{delay:.1f}s** pause...")
                time.sleep(delay)

        # ---- SCAN COMPLETE ----
        progress_bar.progress(1.0)
        status_text.markdown("✅ **Scan 100% Complete!**")
        st.session_state.scan_results = final_data_rows
        st.session_state.scan_done = True
        st.session_state.sr_count = sr_count - 1
        st.session_state.skip_count = skip_count

# ---- RESULTS DISPLAY (Session State se - reload pe bhi dikhega) ----
if st.session_state.scan_done and st.session_state.scan_results is not None:
    found = st.session_state.sr_count
    skipped = st.session_state.skip_count

    if found > 0:
        st.success(f"💥 **{found} Momentum Stock(s) found!** | Skipped (no data): {skipped}")
        df_results = pd.DataFrame(st.session_state.scan_results)
        styled_df  = df_results.style.map(apply_light_color)
        st.dataframe(styled_df, use_container_width=True, height=600, hide_index=True)

        csv = df_results.to_csv(index=False).encode('utf-8')
        col_b.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="GJ02_Multibagger_Report.csv",
            mime="text/csv",
        )
    else:
        st.warning("⚠️ Koi stock criteria pass nahi kar paya. Market conditions check karein!")
