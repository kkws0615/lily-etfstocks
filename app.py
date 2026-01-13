import streamlit as st
import yfinance as yf
import pandas as pd

# --- 設定頁面 ---
st.set_page_config(page_title="台股 ETF 百大配息榜", layout="wide")
st.title("📈 台股百大熱門 ETF 配息排行 & 存股計算機")

# --- 初始化 Session State ---
if 'stock_df' not in st.session_state:
    st.session_state.stock_df = pd.DataFrame()
# 新增：用於儲存使用者選擇的投資組合
if 'portfolio_list' not in st.session_state:
    st.session_state.portfolio_list = []

# --- 表格樣式設定 ---
TABLE_CONFIG = {
    "代號": st.column_config.LinkColumn(
        "代號", display_text=r"quote/(.*)", help="點擊前往 Yahoo 股市"
    ),
    "配息明細 (近1年)": st.column_config.TextColumn("近1年配息明細 (元/股)", width="medium"),
    "現價 (元)": st.column_config.NumberColumn(format="$ %.2f"),
    "近一年配息 (每張)": st.column_config.NumberColumn(format="$ %d"),
    "等值月配息 (每張)": st.column_config.NumberColumn(format="$ %d"),
    "年殖利率 (%)": st.column_config.ProgressColumn(format="%.2f%%", min_value=0, max_value=15),
}

# --- 內建：台股百大熱門 ETF 資料庫 ---
ETF_DB = {
    # === 高股息 ===
    "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", "00929.TW": "復華台灣科技優息", 
    "00919.TW": "群益台灣精選高息", "00940.TW": "元大台灣價值高息", "00939.TW": "統一台灣高息動能",
    "00713.TW": "元大台灣高息低波", "00900.TW": "富邦特選高股息30", "00915.TW": "凱基優選高股息30",
    "00918.TW": "大華優利高填息30", "00934.TW": "中信成長高股息", "00936.TW": "台新永續高息中小",
    "00944.TW": "野村趨勢動能高息", "00946.TW": "群益科技高息成長", "00943.TW": "兆豐電子高息等權",
    "00701.TW": "國泰股利精選30", "00731.TW": "復華富時高息低波", "00690.TW": "兆豐臺灣藍籌30",
    "00730.TW": "富邦臺灣優質高息", "00907.TW": "永豐優息存股", "00932.TW": "兆豐永續高息等權",
    "00927.TW": "群益半導體收益",
    # === 市值/科技/債券/其他 ===
    "0050.TW": "元大台灣50", "006208.TW": "富邦台50", "00692.TW": "富邦公司治理", 
    "00922.TW": "國泰台灣領袖50", "00923.TW": "群益台灣ESG低碳", "00850.TW": "元大臺灣ESG永續",
    "0051.TW": "元大中型100", "006204.TW": "永豐臺灣加權", "0057.TW": "富邦摩台",
    "006203.TW": "元大MSCI台灣", "00921.TW": "兆豐龍頭等權", "00905.TW": "FT臺灣Smart",
    "0052.TW": "富邦科技", "0053.TW": "元大電子", "00881.TW": "國泰台灣5G+",
    "00891.TW": "中信關鍵半導體", "00892.TW": "富邦台灣半導體", "00830.TW": "國泰費城半導體",
    "00935.TW": "野村臺灣新科技50", "00941.TW": "中信上游半導體", "00893.TW": "國泰智能電動車",
    "00895.TW": "富邦未來車", "00901.TW": "永豐智能車供應鏈", "00733.TW": "富邦臺灣中小",
    "0055.TW": "元大MSCI金融", "00938.TW": "凱基優選30",
    "00679B.TW": "元大美債20年", "00687B.TW": "國泰20年美債", "00937B.TW": "群益ESG投等債20+",
    "00933B.TW": "國泰10Y+金融債", "00720B.TW": "元大投資級公司債", "00725B.TW": "國泰投資級公司債",
    "00751B.TW": "元大AAA至A公司債", "00772B.TW": "中信高評級公司債", "00795B.TW": "中信美國公債20年",
    "00680L.TW": "元大美債20正2", "00688L.TW": "國泰20年美債正2", "00857B.TW": "永豐20年美債",
    "00724B.TW": "群益10年IG金融債", "00746B.TW": "富邦A級公司債", "00740B.TW": "富邦全球投等債",
    "00662.TW": "富邦NASDAQ", "00646.TW": "元大S&P500", "00757.TW": "統一FANG+",
    "006205.TW": "富邦上証", "0061.TW": "元大寶滬深", "00636.TW": "國泰中國A50",
    "00882.TW": "中信中國高股息", "00885.TW": "富邦越南", "00909.TW": "國泰數位支付服務",
    "00861.TW": "元大全球未來通訊", "00762.TW": "元大全球AI", "00851.TW": "台新全球AI",
    "00631L.TW": "元大台灣50正2", "00632R.TW": "元大台灣50反1", "00673R.TW": "元大SP500反1",
    "00650L.TW": "復華香港正2", "00655L.TW": "國泰中國A50正2"
}

etf_options = [f"{code} {name}" for code, name in ETF_DB.items()]

# --- 函數：即時掃描 (第一區塊用) ---
def get_batch_data(ticker_dict, table_placeholder):
    data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(ticker_dict)
    keys = list(ticker_dict.keys())
    
    for i, ticker in enumerate(keys):
        name = ticker_dict[ticker]
        progress_bar.progress((i + 1) / total)
        status_text.text(f"正在分析 ({i+1}/{total}): {name}...")
        try:
            stock = yf.Ticker(ticker)
            price = stock.fast_info.last_price
            if price is None:
                info = stock.info
                price = info.get('currentPrice', info.get('previousClose', 0))
            if price is None or price == 0: continue

            divs = stock.dividends
            history_str = "無配息"
            total_annual_div = 0
            if not divs.empty:
                one_year_ago = pd.Timestamp.now(tz=divs.index.tz) - pd.Timedelta(days=365)
                last_year_divs = divs[divs.index > one_year_ago]
                total_annual_div = last_year_divs.sum()
                if not last_year_divs.empty:
                    count = len(last_year_divs)
                    if count >= 10: freq_tag = "月"
                    elif count >= 3: freq_tag = "季"
                    elif count == 2: freq_tag = "半"
                    else: freq_tag = "年"
                    vals = [f"{x:.2f}".rstrip('0').rstrip('.') for x in last_year_divs.tolist()]
                    history_str = f"{freq_tag}: {'/'.join(vals)}"

            div_per_sheet_year = total_annual_div * 1000
            avg_monthly_income_sheet = div_per_sheet_year / 12
            yield_rate = (total_annual_div / price) * 100 if price > 0 else 0
            yahoo_url = f"https://tw.stock.yahoo.com/quote/{ticker}"

            new_row = {
                "代號": yahoo_url, "名稱": name, "配息明細 (近1年)": history_str,
                "現價 (元)": price, "近一年配息 (每張)": int(div_per_sheet_year),
                "等值月配息 (每張)": int(avg_monthly_income_sheet), "年殖利率 (%)": yield_rate
            }
            data.append(new_row)
            current_df = pd.DataFrame(data).sort_values(by="等值月配息 (每張)", ascending=False).reset_index(drop=True)
            table_placeholder.dataframe(current_df, column_config=TABLE_CONFIG, use_container_width=True, hide_index=True, height=800)
        except: continue
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(data)

# --- 介面佈局 ---
tab1, tab2 = st.tabs(["🏆 百大 ETF 排行榜", "💰 存股組合計算機"])

# === 第一區塊：排行 ===
with tab1:
    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        start_scan = st.button("🚀 開始掃描 (即時顯示)")
    with col_info:
        st.write(f"目前內建熱門 ETF 清單：共 **{len(ETF_DB)}** 檔")

    table_placeholder = st.empty()

    if start_scan:
        df = get_batch_data(ETF_DB, table_placeholder)
        if not df.empty:
            st.session_state.stock_df = df.sort_values(by="等值月配息 (每張)", ascending=False).reset_index(drop=True)
        else:
            st.error("掃描失敗")

    if not st.session_state.stock_df.empty:
        table_placeholder.empty()
        search_term = st.text_input("🔍 搜尋結果", "")
        df_display = st.session_state.stock_df
        if search_term:
            df_display = df_display[df_display["名稱"].str.contains(search_term, case=False) | df_display["代號"].str.contains(search_term, case=False)]
        st.dataframe(df_display, column_config=TABLE_CONFIG, use_container_width=True, hide_index=True, height=800)
    elif not start_scan:
        st.info("👆 請點擊上方按鈕開始載入資料")

# === 第二區塊：投資組合計算機 ===
with tab2:
    st.header("🛒 自組 ETF 月配息包")
    
    col_input, col_result = st.columns([1, 2])
    
    # --- 左側：新增股票區 ---
    with col_input:
        with st.container(border=True):
            st.subheader("1. 加入股票")
            # 選擇股票
            selected_option = st.selectbox("選擇股票", etf_options)
            
            # 輸入金額
            add_money = st.number_input("預計投入金額 (台幣)", value=100000, step=10000, min_value=0)
            
            if st.button("➕ 加入清單"):
                if selected_option and add_money > 0:
                    with st.spinner("計算中..."):
                        # 解析代號與名稱
                        ticker = selected_option.split(" ")[0]
                        name = selected_option.split(" ")[1]
                        
                        # 抓取即時數據
                        try:
                            stock = yf.Ticker(ticker)
                            price = stock.fast_info.last_price
                            if price is None:
                                info = stock.info
                                price = info.get('currentPrice', info.get('previousClose', 0))
                            
                            if price > 0:
                                # 計算張數
                                price_per_sheet = price * 1000
                                sheets = int(add_money / price_per_sheet)
                                real_cost = sheets * price_per_sheet
                                
                                # 計算配息
                                divs = stock.dividends
                                annual_div_per_share = 0
                                if not divs.empty:
                                    one_year_ago = pd.Timestamp.now(tz=divs.index.tz) - pd.Timedelta(days=365)
                                    annual_div_per_share = divs[divs.index > one_year_ago].sum()
                                
                                total_annual_income = annual_div_per_share * 1000 * sheets
                                avg_monthly_income = total_annual_income / 12
                                
                                # 加入 Session State
                                st.session_state.portfolio_list.append({
                                    "股票": f"{name} ({ticker})",
                                    "投入金額": int(real_cost), # 實際購買成本
                                    "持有張數": f"{sheets} 張",
                                    "預計年配息": int(total_annual_income),
                                    "平均月配": int(avg_monthly_income)
                                })
                                st.success(f"已加入 {sheets} 張 {name}")
                            else:
                                st.error("無法獲取股價")
                        except Exception as e:
                            st.error(f"錯誤: {e}")
                else:
                    st.warning("請輸入有效金額")

            st.write("---")
            if st.button("🗑️ 清空所有清單", type="primary"):
                st.session_state.portfolio_list = []
                st.rerun()

    # --- 右側：顯示結果區 ---
    with col_result:
        st.subheader("2. 您的投資組合預覽")
        
        if len(st.session_state.portfolio_list) > 0:
            # 轉成 DataFrame 顯示
            df_portfolio = pd.DataFrame(st.session_state.portfolio_list)
            
            # 顯示表格
            st.dataframe(
                df_portfolio,
                column_config={
                    "投入金額": st.column_config.NumberColumn(format="$ %d"),
                    "預計年配息": st.column_config.NumberColumn(format="$ %d"),
                    "平均月配": st.column_config.NumberColumn(format="$ %d"),
                },
                use_container_width=True,
                hide_index=True
            )
            
            # 計算總計
            total_invest = df_portfolio["投入金額"].sum()
            total_monthly = df_portfolio["平均月配"].sum()
            portfolio_yield = (total_monthly * 12 / total_invest * 100) if total_invest > 0 else 0
            
            st.divider()
            # 顯示大儀表板
            m1, m2, m3 = st.columns(3)
            m1.metric("總投入金額", f"${total_invest:,}")
            m2.metric("✨ 預估每月領息", f"${total_monthly:,}")
            m3.metric("組合殖利率", f"{portfolio_yield:.2f}%")
            
        else:
            st.info("👈 請從左側加入股票，開始規劃您的現金流！")
