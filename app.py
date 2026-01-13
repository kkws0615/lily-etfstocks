import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# --- 設定頁面 ---
st.set_page_config(page_title="台股 ETF 全市場配息神算", layout="wide")
st.title("📈 台股全市場 ETF 配息排行 & 存股計算機")

# --- 初始化 Session State ---
if 'stock_df' not in st.session_state:
    st.session_state.stock_df = pd.DataFrame()
if 'etf_list' not in st.session_state:
    st.session_state.etf_list = {}

# --- 核心函數：抓取全台 ETF 清單 (爬蟲) ---
@st.cache_data(ttl=86400) # 每天更新一次清單即可
def fetch_tw_etfs():
    try:
        # 來源：台灣證券交易所 本國上市證券國際證券辨識號碼一覽表
        url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
        res = requests.get(url)
        # 讀取 HTML 表格
        dfs = pd.read_html(res.text)
        df = dfs[0]
        
        # 整理資料：設定欄位名稱 (第0列是標題)
        df.columns = df.iloc[0]
        df = df.iloc[1:]
        
        # 篩選：只留 "ETF" 相關的
        # 在「有價證券別」這一欄尋找 ETF
        target_df = df[df['有價證券別'] == 'ETF']
        
        etf_dict = {}
        for index, row in target_df.iterrows():
            code_name = row['有價證券代號及名稱']
            # 格式通常是 "0050 元大台灣50"
            if " " in code_name:
                code, name = code_name.split(" ", 1) # 切割代號與名稱
                # 排除過於冷門或非台幣計價的 (可選)
                etf_dict[f"{code}.TW"] = name
            elif "\u3000" in code_name: # 處理全形空白
                code, name = code_name.split("\u3000", 1)
                etf_dict[f"{code}.TW"] = name
                
        return etf_dict
    except Exception as e:
        st.error(f"抓取 ETF 清單失敗: {e}")
        # 如果爬蟲失敗，回傳備用的基本清單
        return {
            "0050.TW": "元大台灣50", "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息",
            "00929.TW": "復華台灣科技優息", "00919.TW": "群益台灣精選高息", "00940.TW": "元大台灣價值高息"
        }

# --- 核心函數：抓取股價與配息 ---
def get_batch_data(ticker_dict):
    data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(ticker_dict)
    
    # 為了避免 yfinance 被大量請求封鎖，我們分批次或逐個抓取
    # 這裡示範逐個抓取，但因為全台 ETF 有 200+ 檔，會跑比較久，請耐心等候
    
    keys = list(ticker_dict.keys())
    
    for i, ticker in enumerate(keys):
        name = ticker_dict[ticker]
        
        # 更新進度條
        progress = (i + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"正在分析 ({i+1}/{total}): {name} ({ticker})...")
        
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

# --- 預先載入 ETF 清單 ---
if not st.session_state.etf_list:
    with st.spinner("正在連線證交所更新最新 ETF 清單..."):
        st.session_state.etf_list = fetch_tw_etfs()

# 轉換成選單用的列表 (給第二區塊用)
etf_options = [f"{code} {name}" for code, name in st.session_state.etf_list.items()]


# --- 介面佈局 ---
tab1, tab2 = st.tabs(["🏆 全台 ETF 配息排行", "💰 存股計算機 (以張為單位)"])

# === 第一區塊：排行 ===
with tab1:
    col_btn, col_count = st.columns([1, 4])
    with col_btn:
        # 因為數量多 (約240檔)，提醒使用者
        if st.button("🚀 開始掃描全市場"):
            st.toast("開始掃描約 200+ 檔 ETF，這需要幾分鐘，請稍候...", icon="⏳")
            df = get_batch_data(st.session_state.etf_list)
            if not df.empty:
                st.session_state.stock_df = df.sort_values(by="等值月配息 (每張)", ascending=False).reset_index(drop=True)
            else:
                st.error("無法獲取資料，請稍後再試")
    
    with col_count:
        st.write(f"目前資料庫共有 **{len(st.session_state.etf_list)}** 檔上市 ETF")

    # 顯示搜尋與表格
    if not st.session_state.stock_df.empty:
        
        search_term = st.text_input("🔍 搜尋結果 (輸入關鍵字後按 Enter)", "")
        
        df_display = st.session_state.stock_df
        if search_term:
            df_display = df_display[
                df_display["名稱"].str.contains(search_term, case=False) | 
                df_display["代號"].str.contains(search_term, case=False)
            ]

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
        st.info("👆 全市場掃描較耗時 (約 3~5 分鐘)，點擊按鈕後請喝杯咖啡稍等。")

# === 第二區塊：計算機 ===
with tab2:
    st.header("每「張」股票配息試算")
    col1, col2 = st.columns(2)
    
    with col1:
        # 這裡現在包含全部 ETF 了
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
