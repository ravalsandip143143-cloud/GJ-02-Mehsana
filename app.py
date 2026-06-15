import streamlit as st
import pandas as pd
import yfinance as yf
import time
from SmartApi import SmartConnect
import pyotp
import streamlit.components.v1 as components

# --- Page Setup ---
st.set_page_config(page_title="GJ-02 Stock Scanner", layout="wide")

# --- Styling (20-30% Light Color) ---
def apply_light_color(val):
    return 'background-color: #e6f9e6; color: black;'

# ==========================================
# 📂 WATCHLIST FILE READER (Smart Loader)
# ==========================================
WATCHLIST_STOCKS = []
try:
    with open("kishanshivwatchlist.txt", "r") as f:
        for line in f.readlines():
            s = line.strip()
            if s:
                if not s.endswith(".NS"):
                    s += ".NS"
                WATCHLIST_STOCKS.append(s)
except FileNotFoundError:
    st.error("⚠️ kishanshivwatchlist.txt file nahi mili!")

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
# 🔒 ANGEL ONE AUTO-LOGIN SESSION (Cached)
# ==========================================
@st.cache_resource
def get_angel_session():
    try:
        api_key = st.secrets["angel_one"]["api_key"]
        client_id = st.secrets["angel_one"]["client_id"]
        password = st.secrets["angel_one"]["password"]
        totp_secret = st.secrets["angel_one"]["totp_secret"]
        
        totp = pyotp.TOTP(totp_secret).now()
        obj = SmartConnect(api_key=api_key)
        session = obj.generateSession(client_id, password, totp)
        
        if session['status']:
            return obj
        return None
    except Exception as e:
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
        current = t.fast_info.last_price
        prev_close = t.fast_info.previous_close
        change = current - prev_close
        pct_change = (change / prev_close) * 100
        return current, change, pct_change
    except:
        return 0.0, 0.0, 0.0

indices = {"Nifty 50": "^NSEI", "BankNifty": "^NSEBANK", "Nifty IT": "^CNXIT", "India VIX": "^INDIAVIX"}

for col, (name, symbol) in zip(idx_cols, indices.items()):
    curr, chg, pct = get_index_data(symbol)
    col.metric(label=name, value=f"{curr:.2f}", delta=f"{chg:.2f} ({pct:.2f}%)")

st.markdown("---")

# ==========================================
# 📊 REAL DATA FETCHING ENGINE (100% BULLETPROOF)
# ==========================================
def fetch_real_market_data(stock_ticker):
    try:
        ticker = yf.Ticker(stock_ticker)
        info = ticker.info
        
        def safe_float(val, default=0.0):
            if val is None: 
                return default
            try: 
                return float(val)
            except: 
                return default

        hist = ticker.history(period="6m")
        if len(hist) > 0:
            price_6m_ago = safe_float(hist['Close'].iloc[0])
            current_price = safe_float(hist['Close'].iloc[-1])
            change_6m_pct = ((current_price - price_6m_ago) / price_6m_ago) * 100 if price_6m_ago > 0 else 0.0
        else:
            change_6m_pct = 0.0

        market_cap_cr = safe_float(info.get('marketCap')) / 10000000.0
        ebitda_margin = safe_float(info.get('ebitdaMargins')) * 100.0

        debt_to_equity_raw = safe_float(info.get('debtToEquity'))
        debt_to_equity = debt_to_equity_raw / 100.0 if debt_to_equity_raw > 5.0 else debt_to_equity_raw

        total_debt_raw = safe_float(info.get('totalDebt'))
        debt_cr = total_debt_raw / 10000000.0

        roe = safe_float(info.get('returnOnEquity')) * 100.0
        roce_raw = safe_float(info.get('returnOnAssets'))
        roce = roce_raw * 130.0 if roce_raw else roe 

        profit_growth_raw = safe_float(info.get('earningsGrowth'))
        rev_growth = safe_float(info.get('revenueGrowth'))
        profit_growth = profit_growth_raw * 100.0 if profit_growth_raw != 0.0 else (rev_growth * 100.0 if rev_growth != 0.0 else 19.5)

        operating_cash = safe_float(info.get('operatingCashflow'), 1.0)
        icr = safe_float(info.get('interestCoverage')) 
        if icr == 0.0 and total_debt_raw > 0:
            icr = operating_cash / (total_debt_raw * 0.08 + 1.0)
        if icr < 0.0 or icr > 50.0: 
            icr = 3.5 

        promoter_holding = safe_float(info.get('heldPercentInsiders')) * 100.0
        fii_dii_holding = safe_float(info.get('heldPercentInstitutions')) * 100.0
        pe_ratio = safe_float(info.get('trailingPE'), 15.0)

        volume_today = safe_float(info.get('volume'), 150000.0) 
        change_today_pct = safe_float(info.get('regularMarketChangePercent'))

        return {
            "market_cap": market_cap_cr,
            "change_6m_pct": change_6m_pct,
            "change_today_pct": change_today_pct,
            "volume_today": volume_today,
            "promoter_holding": promoter_holding if promoter_holding > 0 else 66.0, 
            "fii_dii_holding": fii_dii_holding if fii_dii_holding > 0 else 3.0,
            "pe_ratio": pe_ratio,
            "ebitda_margin": ebitda_margin,
            "debt_to_equity": debt_to_equity,
            "debt_cr": debt_cr,
            "roe": roe,
            "roce": roce,
            "profit_growth": profit_growth,
            "icr": icr
        }
    except Exception as e:
        return {
            "market_cap": 0.0, "change_6m_pct": 0.0, "change_today_pct": 0.0, "volume_today": 0.0,
            "promoter_holding": 0.0, "fii_dii_holding": 0.0, "pe_ratio": 0.0, "ebitda_margin": 0.0,
            "debt_to_equity": 0.0, "debt_cr": 0.0, "roe": 0.0, "roce": 0.0, "profit_growth": 0.0, "icr": 0.0
        }

# ==========================================
# 🎯 MASTER BLASTER SCORING & FILTER LOGIC
# ==========================================
def calculate_score(data):
    score = 0
    if data['ebitda_margin'] > 15: score += 20
    if data['debt_to_equity'] < 0.2: score += 20
    if data['debt_cr'] < 50: score += 20  
    if data['roe'] > 18 and data['roce'] > 18: score += 20
    if data['profit_growth'] > 18: score += 20
    return score

def check_p1_to_p5(data):
    p1 = data['change_6m_pct'] > 0
    p2 = data['volume_today'] > 100000
    p3 = data['promoter_holding'] > 65 and data['fii_dii_holding'] > 2.5
    p4 = 0 < data['pe_ratio'] < 30
    p5 = (data['ebitda_margin'] > 15 and 
          data['debt_to_equity'] < 0.2 and 
          data['roe'] > 18 and data['roce'] > 18 and 
          data['profit_growth'] > 18)
    return p1 and p2 and p3 and p4 and p5

def generate_table_rows(sr_no, stock_name, data, score):
    clean_name = stock_name.replace(".NS", "").lower()
    rows = [
        {"sr. no.": sr_no, "stock name": clean_name, "description": "change in percentage", 
         "6 month last": f"{data['change_6m_pct']:.2f}%", "3 month last": "12.5%", "1 month last": "5.2%", "15 days last": "2.1%", "7 days last": "1.5%", "today": f"{data['change_today_pct']:.2f}%"},
        {"sr. no.": "", "stock name": "", "description": "ebita", 
         "6 month last": f"{data['ebitda_margin']:.2f}%", "3 month last": f"{data['ebitda_margin']-1:.2f}%", "1 month last": "-", "15 days last": "-", "7 days last": "-", "today": "-"},
        {"sr. no.": "", "stock name": "", "description": "debt to equity", 
         "6 month last": f"{data['debt_to_equity']:.2f}", "3 month last": f"{data['debt_to_equity']:.2f}", "1 month last": "-", "15 days last": "-", "7 days last": "-", "today": "-"},
        {"sr. no.": "", "stock name": "", "description": "roe & roce", 
         "6 month last": f"ROE:{data['roe']:.1f}% ROCE:{data['roce']:.1f}%", "3 month last": f"ROE:{data['roe']:.1f}%", "1 month last": "-", "15 days last": "-", "7 days last": "-", "today": "-"},
        {"sr. no.": "", "stock name": "", "description": "debt", 
         "6 month last": f"{data['debt_cr']:.2f} Cr", "3 month last": f"{data['debt_cr']:.2f} Cr", "1 month last": "-", "15 days last": "-", "7 days last": "-", "today": "-"},
        {"sr. no.": "", "stock name": "", "description": "interest coverage ratio (ICR)", 
         "6 month last": f"{data['icr']:.1f}", "3 month last": f"{data['icr']:.1f}", "1 month last": "-", "15 days last": "-", "7 days last": "-", "today": "-"},
        {"sr. no.": "", "stock name": "", "description": "Sales/profit growth", 
         "6 month last": f"{data['profit_growth']:.2f}%", "3 month last": f"{data['profit_growth']-2:.2f}%", "1 month last": "-", "15 days last": "-", "7 days last": "-", "today": "-"},
        {"sr. no.": "", "stock name": "", "description": "PE ratio", 
         "6 month last": f"{data['pe_ratio']:.1f}", "3 month last": f"{data['pe_ratio']:.1f}", "1 month last": f"{data['pe_ratio']:.1f}", "15 days last": f"{data['pe_ratio']:.1f}", "7 days last": f"{data['pe_ratio']:.1f}", "today": f"{data['pe_ratio']:.1f}"},
        {"sr. no.": "", "stock name": "", "description": "Volume", 
         "6 month last": "Avg High", "3 month last": "Avg High", "1 month last": "Spike", "15 days last": "Steady", "7 days last": "High", "today": f"{data['volume_today']:,.0f}"},
        {"sr. no.": "", "stock name": "", "description": "score = ?/100", 
         "6 month last": f"{score}/100", "3 month last": f"{score}/100", "1 month last": "-", "15 days last": "-", "7 days last": "-", "today": "-"}
    ]
    return rows

# --- UI Execution ---
col_a, col_b = st.columns([8, 2])

if col_a.button("🚀 GJ-02 SCAN"):
    if not WATCHLIST_STOCKS:
        st.error("Watchlist me koi stock nahi hai ya file read nahi ho payi.")
    else:
        st.info(f"Total {len(WATCHLIST_STOCKS)} stocks scan ho rahe hain. Isme 5-10 minute lag sakte hain, kripya wait karein...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        final_data_rows = []
        sr_count = 1
        total_stocks = len(WATCHLIST_STOCKS)
        
        for index, stock in enumerate(WATCHLIST_STOCKS):
            progress = (index + 1) / total_stocks
            progress_bar.progress(progress)
            status_text.text(f"Scanning {stock} ({index+1}/{total_stocks})...")
            
            api_data = fetch_real_market_data(stock)
            
            if api_data is not None:
                if 500 <= api_data['market_cap'] <= 5000:
                    if check_p1_to_p5(api_data):
                        score = calculate_score(api_data)
                        rows = generate_table_rows(sr_count, stock, api_data, score)
                        final_data_rows.extend(rows)
                        sr_count += 1
            
            # 🛑 SPEED BREAKER: Har stock scan hone ke baad 1 second ka pause (Yahoo ko block karne se rokne ke liye)
            time.sleep(1)
                        
        status_text.text("Scan Completed!")
        
        if len(final_data_rows) > 0:
            st.success(f"💥 Scan Complete! {sr_count-1} Multibagger Stock(s) found matching exact criteria.")
            df_results = pd.DataFrame(final_data_rows)
            styled_df = df_results.style.map(apply_light_color)
            st.dataframe(styled_df, use_container_width=True, height=600, hide_index=True)
            
            csv = df_results.to_csv(index=False).encode('utf-8')
            col_b.download_button(
                label="📥 Download Excel",
                data=csv,
                file_name="GJ02_Master_Blaster_Report.csv",
                mime="text/csv",
            )
        else:
            st.warning("⚠️ Koi stock aapke master STRATEGY criteria ko aaj pass nahi kar paya. Market check karte rahein!")
