import streamlit as st
import pandas as pd
import random # Sirf dummy calculation ke liye, baad me API lagayenge
import time

# --- Page Setup ---
st.set_page_config(page_title="GJ-02, Mahesana", layout="wide")

# --- Styling (20-30% Light Color) ---
def apply_light_color(val):
    # Light green with ~20% opacity look (Hex code with transparency nahi chalta easily, so light pastel hex)
    return 'background-color: #e6f9e6; color: black;'

# --- Your Logic Parameters ---
WATCHLIST_NAME = "kishanshiv whatchlist"
# Dummy watchlist of small-caps
WATCHLIST_STOCKS = ["RAILTEL", "RVNL", "SUZLON", "TRIDENT", "IRFC", "ZOMATO"]

def fetch_api_data(stock_name):
    # YAHAN AAPKA API CONNECT HOGA (Angel One / Kotak Neo)
    # Abhi ke liye hum aapke P1 to P5 logic ko test karne ke liye data mock kar rahe hain
    
    # Randomly generating data that MIGHT pass your strict logic
    return {
        "market_cap": random.uniform(400, 6000), # 500-5000 Cr filter
        "change_6m_pct": random.uniform(-10, 150),
        "change_today_pct": random.uniform(-2, 10),
        "volume_today": random.randint(10000, 5000000),
        "promoter_holding": random.uniform(40, 75),
        "fii_dii_holding": random.uniform(0, 10),
        "pe_ratio": random.uniform(5, 50),
        "ebitda_margin": random.uniform(5, 25),
        "debt_to_equity": random.uniform(0, 1.5),
        "debt_cr": random.uniform(0, 500),
        "roe": random.uniform(5, 30),
        "roce": random.uniform(5, 30),
        "profit_growth": random.uniform(-10, 40),
        "icr": random.uniform(1, 10)
    }

def calculate_score(data):
    score = 0
    # 20 points for each of the 5 criteria
    if data['ebitda_margin'] > 15: score += 20
    if data['debt_to_equity'] < 0.2: score += 20
    if data['debt_cr'] < 50: score += 20  # Assuming < 50Cr debt is manageable for small cap
    if data['roe'] > 18 and data['roce'] > 18: score += 20
    if data['profit_growth'] > 18: score += 20
    return score

def check_p1_to_p5(data):
    # P1: 6 month positive
    p1 = data['change_6m_pct'] > 0
    # P2: Volume Achha ho (> 1,00,000)
    p2 = data['volume_today'] > 100000
    # P3: Promoter > 65%, FII/DII > 2.5%
    p3 = data['promoter_holding'] > 65 and data['fii_dii_holding'] > 2.5
    # P4: PE Ratio Achha ho (0 se 30 ke beech)
    p4 = 0 < data['pe_ratio'] < 30
    # P5: Strict Fundamental Check
    p5 = (data['ebitda_margin'] > 15 and 
          data['debt_to_equity'] < 0.2 and 
          data['roe'] > 18 and data['roce'] > 18 and 
          data['profit_growth'] > 18)
    
    return p1 and p2 and p3 and p4 and p5

def generate_table_rows(sr_no, stock_name, data, score):
    # Dhyan rahe: Jo quarterly aata hai, usme short timeframes me "-" lagana hai
    rows = [
        {"sr. no.": sr_no, "stock name": stock_name, "description": "change in percentage", 
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
         "6 month last": f"{data['pe_ratio']+5:.1f}", "3 month last": f"{data['pe_ratio']+2:.1f}", "1 month last": f"{data['pe_ratio']+1:.1f}", "15 days last": f"{data['pe_ratio']:.1f}", "7 days last": f"{data['pe_ratio']:.1f}", "today": f"{data['pe_ratio']:.1f}"},
         
        {"sr. no.": "", "stock name": "", "description": "Volume", 
         "6 month last": "Avg High", "3 month last": "Avg High", "1 month last": "Spike", "15 days last": "Steady", "7 days last": "High", "today": f"{data['volume_today']}"},
         
        {"sr. no.": "", "stock name": "", "description": "score = ?/100", 
         "6 month last": f"{score}/100", "3 month last": f"{score}/100", "1 month last": "-", "15 days last": "-", "7 days last": "-", "today": "-"}
    ]
    return rows

# --- UI & Execution ---
st.title("🎯 Master Blaster Multibagger Scanner")
st.write(f"Scanning from: **{WATCHLIST_NAME}**")

col_a, col_b = st.columns([8, 2])

if col_a.button("🚀 Start P1-P5 Master Scan"):
    with st.spinner('Connecting to API & Scanning Market Data...'):
        time.sleep(2) # Fake API loading time
        
        final_data_rows = []
        sr_count = 1
        
        # Scanning each stock in watchlist
        for stock in WATCHLIST_STOCKS:
            api_data = fetch_api_data(stock)
            
            # Market Cap Check (500 to 5000 Cr)
            if 500 <= api_data['market_cap'] <= 5000:
                # P1 to P5 strict check
                if check_p1_to_p5(api_data):
                    score = calculate_score(api_data)
                    rows = generate_table_rows(sr_count, stock, api_data, score)
                    final_data_rows.extend(rows)
                    sr_count += 1
        
        if len(final_data_rows) > 0:
            st.success(f"Scan Complete! {sr_count-1} Multibagger(s) found matching exact criteria.")
            df_results = pd.DataFrame(final_data_rows)
            
            # Applying 20-30% light color styling
            styled_df = df_results.style.map(apply_light_color)
            
            # Displaying Table
            st.dataframe(styled_df, use_container_width=True, height=600, hide_index=True)
            
            # Download Button (Top Right Corner via column layout)
            csv = df_results.to_csv(index=False).encode('utf-8')
            col_b.download_button(
                label="📥 Download Excel/CSV",
                data=csv,
                file_name="Master_Blaster_Report.csv",
                mime="text/csv",
            )
        else:
            st.warning("Koi stock aapke strict P1-P5 master criteria ko aaj pass nahi kar paya. Market check karte rahein!")
else:
    st.info("👈 Scan start karne ke liye 'Start P1-P5 Master Scan' par click karein.")