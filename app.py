import streamlit as st
import yfinance as yf
import pandas as pd

# --- 設定頁面 ---
st.set_page_config(page_title="台股 ETF 配息神算", layout="wide")
st.title("📈 台股 ETF 配息排行 & 存股計算機")

# --- 初始化 Session State (讓資料不會消失) ---
if 'stock_df' not in st.session_state:
    st.session_state.stock_df = pd.DataFrame()

# --- 內建 ETF 資料庫 ---
ETF_DB = {
    "0050.TW": "元大台灣50", "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", "00929.TW": "復華台灣科技優息",
    "00919.TW": "群益台灣精選高息", "00940.TW": "元大台灣價值高息", "00939.TW": "統一台灣高息動能", "006208.TW": "富邦台50",
    "00713.TW": "元大台灣高息低波", "00900.TW": "富邦特選高股息30", "00881.TW": "國泰台灣5G+", "00692.TW": "富邦公司治理",
    "0051.TW": "元大中型100", "0052.TW": "富邦科技", "00631L.TW": "元大台灣50正2", "00632R.TW": "元大台灣50反1",
    "00679B.TW": "元大美債20年", "00687B.TW": "國泰20年美債", "00937B.TW": "群益ESG投等債20+", "00751B.TW": "元大AAA至A公司債",
    "00720B.TW": "元大投資級公司債", "00725B.TW": "國泰投資級公司債", "00850.TW": "元大臺灣ESG永續", "00923.TW": "群益台灣ESG低碳",
    "0053.TW": "元大電子", "0055.TW": "元大MSCI金融", "0057.TW": "富邦摩台", "006203.TW": "元大MSCI台灣",
    "006204.TW": "永豐臺灣加權", "00662.TW": "富邦NASDAQ", "00646.TW": "元大S&P500", "00830.TW": "國泰費城半導體",
    "00891.TW": "中信關鍵半導體", "00892.TW": "富邦台灣半導體", "00893.TW": "國泰智能電動車", "00895.TW": "富邦未來車",
    "00905.TW": "FT臺灣Smart", "00918.TW": "大華優利高填息30", "00915.TW": "凱基優選高股息30", "00922.TW": "國泰台灣領袖50",
    "00927.TW": "群益半導體收益", "00932.TW": "兆豐永續高息等權", "00934.TW": "中信成長高股息", "00935.TW": "野村臺灣新科技50",
    "00936.TW": "台新永續高息中小"
}

etf_options = [f"{code} {name}" for code, name in ETF_DB.items()]

# --- 核心函數 ---
def get_batch_data(ticker_dict):
    data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(ticker_dict)
    
    for i, (ticker, name) in enumerate(ticker_dict.items()):
        progress = (i + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"正在分析: {name} ({ticker})...")
        
        try:
            stock = yf.Ticker(ticker)
            price = stock.fast_info.last_price
            if price is None:
                info = stock.info
                price = info.get('currentPrice', info.get('previousClose', 0))

            if price is None or price == 0:
                continue

            # 配息處理
            divs = stock.dividends
            history_str = "無配息"
            total_annual_div = 0
            
            if not divs.empty:
                one_year_ago = pd.Timestamp.now(tz=divs.index.tz) - pd.Timedelta(days=365)
                last_year_divs = divs[divs.index > one_year_ago]
                
                total_annual_div = last_year_divs.sum()
                
                if not last_year_divs.empty:
                    # 判斷頻率
                    count = len(last_year_divs)
                    if count >= 10: freq_tag = "月"
                    elif count >= 3: freq_tag = "季"
                    elif count == 2: freq_tag = "半"
                    else: freq_tag = "年"
                    
                    # 格式化金額
                    vals = [f"{x:.2f}".rstrip('0').rstrip('.') for x in last_year_divs.tolist()]
                    history_str = f"{freq_tag}: {'/'.join(vals)}"

            # 計算數據
            div_per_sheet_year = total_annual_div * 1000
            avg_monthly_income_sheet = div_per_sheet_year / 12
            yield_rate = (total_annual_div / price) * 100 if price > 0 else 0

            # Yahoo 網址
            yahoo_url = f"https://tw.stock.yahoo.com/quote/{ticker}"

            data.append({
                "代號": yahoo_url, 
                "名稱": name,
                "配息明細 (近1年)": history_str,
                "現價 (元)": price,
                "近一年配息 (每張)": int(div_per_sheet_year),
                "等值月配息 (每張)": int(avg_monthly_income_sheet),
                "年殖利率 (%)": yield_rate
            })
        except Exception as e:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(data)

# --- 介面佈局 ---
tab1, tab2 = st.tabs(["🏆 前 100 高配息排行", "💰 存股計算機 (以張為單位)"])

# === 第一區塊：排行 ===
with tab1:
    # 1. 抓取資料按鈕
    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        if st.button("🔄 開始掃描 / 更新資料"):
            df = get_batch_data(ETF_DB)
            if not df.empty:
                # 存入 Session State
                st.session_state.stock_df = df.sort_values(by="等值月配息 (每張)", ascending=False).head(100).reset_index(drop=True)
            else:
                st.error("無法獲取資料，請稍後再試")

    # 2. 顯示搜尋與表格 (只要 Session State 有資料就顯示)
    if not st.session_state.stock_df.empty:
        
        # 搜尋框
        search_term = st.text_input("🔍 關鍵字搜尋 (輸入後請按 Enter，例如: 009, 元大, 債)", "")
        
        # 篩選邏輯
        df_display = st.session_state.stock_df
        if search_term:
            df_display = df_display[
                df_display["名稱"].str.contains(search_term, case=False) | 
                df_display["代號"].str.contains(search_term, case=False)
            ]

        # 顯示表格
        st.dataframe(
            df_display,
            column_config={
                "代號": st.column_config.LinkColumn(
                    "代號", 
                    display_text=r"quote/(.*)", 
                    help="點擊前往 Yahoo 股市" 
                ),
                "配息明細 (近1年)": st.column_config.TextColumn(
                    "近1年配息明細 (元/股)",
                    width="medium"
                ),
                "現價 (元)": st.column_config.NumberColumn(format="$ %.2f"),
                "近一年配息 (每張)": st.column_config.NumberColumn(format="$ %d"),
                "等值月配息 (每張)": st.column_config.NumberColumn(format="$ %d"),
                "年殖利率 (%)": st.column_config.ProgressColumn(
                    format="%.2f%%", min_value=0, max_value=15
                ),
            },
            use_container_width=True,
            hide_index=True,
            height=800 
        )
    else:
        st.info("👆 請點擊上方按鈕載入最新資料")

# === 第二區塊：計算機 ===
with tab2:
    st.header("每「張」股票配息試算")
    col1, col2 = st.columns(2)
    
    with col1:
        selected_option = st.selectbox("🔍 搜尋並選擇 ETF/股票", etf_options)
        if selected_option:
            ticker = selected_option.split(" ")[0]
            name = selected_option.split(" ")[1]
            stock = yf.Ticker(ticker)
            price = stock.fast_info.last_price
            if price is None:
                 info = stock.info
                 price = info.get('currentPrice', info.get('previousClose', 0))
            
            divs = stock.dividends
            if not divs.empty:
                one_year_ago = pd.Timestamp.now(tz=divs.index.tz) - pd.Timedelta(days=365)
                annual_div_share = divs[divs.index > one_year_ago].sum()
            else:
                annual_div_share = 0

            price_per_sheet = price * 1000
            monthly_income_per_sheet = (annual_div_share * 1000) / 12
            
            st.divider()
            st.metric("股票名稱", f"{name} ({ticker})")
            st.metric("目前股價 (每股)", f"${price:.2f}")
            st.metric("買一張成本", f"${int(price_per_sheet):,}")
            st.metric("平均每張每月可領", f"${int(monthly_income_per_sheet):,}")

    with col2:
        investment_amount = st.number_input("💰 預計投入金額 (台幣)", value=100000, step=10000)
        if selected_option and price > 0:
            sheets_can_buy = int(investment_amount / price_per_sheet)
            remainder_money = investment_amount - (sheets_can_buy * price_per_sheet)
            total_monthly_income = sheets_can_buy * monthly_income_per_sheet
            
            st.divider()
            st.subheader("試算結果")
            st.success(f"可買進 **{sheets_can_buy}** 張")
            if sheets_can_buy > 0:
                st.info(f"預估每月總共可領: **NT$ {int(total_monthly_income):,}** 元")
            else:
                st.warning("資金不足以買進一張")
            st.caption(f"剩餘資金: ${int(remainder_money):,} (不足一張)")
