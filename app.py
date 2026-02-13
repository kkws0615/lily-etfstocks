import streamlit as st
import yfinance as yf
import pandas as pd

# --- 設定頁面 ---
st.set_page_config(page_title="台股 ETF 存股計算機", layout="wide")
st.title("📈 台股 ETF 存股 & 質押試算神器")

# --- 初始化 Session State ---
if 'stock_df' not in st.session_state:
    st.session_state.stock_df = pd.DataFrame()
if 'portfolio_list' not in st.session_state:
    st.session_state.portfolio_list = []

# --- 表格樣式 ---
TABLE_CONFIG = {
    "代號": st.column_config.LinkColumn("代號", display_text=r"quote/(.*)"),
    "配息明細 (近1年)": st.column_config.TextColumn("近1年配息明細", width="medium"),
    "現價 (元)": st.column_config.NumberColumn(format="$ %.2f"),
    "近一年配息 (每張)": st.column_config.NumberColumn(format="$ %d"),
    "等值月配息 (每張)": st.column_config.NumberColumn(format="$ %d"),
    "年殖利率 (%)": st.column_config.ProgressColumn(format="%.2f%%", min_value=0, max_value=15),
}

# --- 內建資料庫 ---
ETF_DB = {
    "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", "00929.TW": "復華台灣科技優息", 
    "00919.TW": "群益台灣精選高息", "00940.TW": "元大台灣價值高息", "00939.TW": "統一台灣高息動能",
    "00713.TW": "元大台灣高息低波", "0050.TW": "元大台灣50", "006208.TW": "富邦台50",
    "00922.TW": "國泰台灣領袖50", "00679B.TW": "元大美債20年", "00687B.TW": "國泰20年美債",
    "00937B.TW": "群益ESG投等債20+", "0052.TW": "富邦科技", "00830.TW": "國泰費城半導體",
    "00881.TW": "國泰台灣5G+", "00662.TW": "富邦NASDAQ", "00646.TW": "元大S&P500"
}
etf_options = [f"{code} {name}" for code, name in ETF_DB.items()]

# --- 核心函數：抓取股價與配息 ---
def get_batch_data(ticker_dict, table_placeholder):
    data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(ticker_dict)
    keys = list(ticker_dict.keys())
    
    for i, ticker in enumerate(keys):
        name = ticker_dict[ticker]
        progress_bar.progress((i + 1) / total)
        status_text.text(f"分析中: {name}...")
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
tab1, tab2 = st.tabs(["🏆 百大 ETF 排行榜", "💰 存股組合 & 質押試算"])

# === Tab 1: 排行 ===
with tab1:
    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        start_scan = st.button("🚀 開始掃描")
    with col_info:
        st.write(f"資料庫：共 **{len(ETF_DB)}** 檔")

    table_placeholder = st.empty()
    if start_scan:
        df = get_batch_data(ETF_DB, table_placeholder)
        if not df.empty:
            st.session_state.stock_df = df.sort_values(by="等值月配息 (每張)", ascending=False).reset_index(drop=True)

    if not st.session_state.stock_df.empty:
        table_placeholder.empty()
        search = st.text_input("🔍 搜尋", "")
        df_show = st.session_state.stock_df
        if search:
            df_show = df_show[df_show["名稱"].str.contains(search, case=False) | df_show["代號"].str.contains(search, case=False)]
        st.dataframe(df_show, column_config=TABLE_CONFIG, use_container_width=True, hide_index=True, height=800)
    elif not start_scan:
        st.info("👆 請點擊按鈕載入資料")

# === Tab 2: 投資組合 & 質押 ===
with tab2:
    st.header("🛒 自組 ETF 投資組合")
    
    col_input, col_result = st.columns([1, 2])
    
    with col_input:
        with st.container(border=True):
            st.subheader("1. 選擇股票")
            selected_option = st.selectbox("選擇股票", etf_options)
            
            # 顯示當前選中股票的基本數據 (不用加入就先給你看)
            if selected_option:
                tk = selected_option.split(" ")[0]
                try:
                    s = yf.Ticker(tk)
                    p = s.fast_info.last_price
                    if p is None: p = s.info.get('currentPrice', 0)
                    st.caption(f"目前股價: {p:.2f} 元")
                except: pass

            add_money = st.number_input("預計投入金額", value=100000, step=10000)
            
            if st.button("➕ 加入投資組合", type="primary"):
                if selected_option and add_money > 0:
                    tk = selected_option.split(" ")[0]
                    nm = selected_option.split(" ")[1]
                    try:
                        s = yf.Ticker(tk)
                        p = s.fast_info.last_price
                        if p is None: p = s.info.get('currentPrice', 0)
                        if p > 0:
                            cost = p * 1000
                            sheets = int(add_money / cost)
                            real_cost = sheets * cost
                            d = s.dividends
                            yr_div = 0
                            if not d.empty:
                                y_ago = pd.Timestamp.now(tz=d.index.tz) - pd.Timedelta(days=365)
                                yr_div = d[d.index > y_ago].sum()
                            
                            ttl_yr = yr_div * 1000 * sheets
                            mnth = ttl_yr / 12
                            
                            st.session_state.portfolio_list.append({
                                "股票": f"{nm} ({tk})",
                                "投入金額": int(real_cost),
                                "持有張數": f"{sheets} 張",
                                "平均月配": int(mnth)
                            })
                            st.success(f"已加入 {sheets} 張")
                    except: pass

            st.divider()
            if st.button("🗑️ 清空清單"):
                st.session_state.portfolio_list = []
                st.rerun()

    with col_result:
        st.subheader("2. 投資組合預覽")
        
        ttl_inv = 0
        ttl_m = 0
        yld = 0

        if len(st.session_state.portfolio_list) > 0:
            df_p = pd.DataFrame(st.session_state.portfolio_list)
            st.dataframe(
                df_p, 
                column_config={
                    "投入金額": st.column_config.NumberColumn(format="$ %d"),
                    "平均月配": st.column_config.NumberColumn(format="$ %d"),
                },
                use_container_width=True, 
                hide_index=True
            )
            
            ttl_inv = df_p["投入金額"].sum()
            ttl_m = df_p["平均月配"].sum()
            yld = (ttl_m * 12 / ttl_inv * 100) if ttl_inv > 0 else 0
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("總投入", f"${ttl_inv:,}")
            c2.metric("✨ 預估月領", f"${ttl_m:,}")
            c3.metric("組合殖利率", f"{yld:.2f}%")
            
            # --- 質押試算區塊 ---
            st.write("---")
            with st.expander("💸 進階功能：股票質押試算 (Leverage)", expanded=True):
                st.info("💡 假設將「上方投資組合」作為擔保品借款，並將借出來的錢「再買入同樣的組合」。")
                
                col_loan1, col_loan2 = st.columns(2)
                with col_loan1:
                    ltv = st.slider("質押成數 (LTV)", 0, 60, 60, 10)
                    interest_rate = st.number_input("借款年利率 (%)", value=2.5, step=0.1)
                
                with col_loan2:
                    max_loan = int(ttl_inv * (ltv / 100))
                    monthly_interest = (max_loan * (interest_rate / 100)) / 12
                    new_monthly_dividend = (max_loan * (yld / 100)) / 12
                    net_monthly_gain = new_monthly_dividend - monthly_interest
                    final_monthly_income = ttl_m + net_monthly_gain
                    
                    # 維持率公式：(原市值+新市值) / 借款
                    maintenance_ratio = ((ttl_inv + max_loan) / max_loan) * 100 if max_loan > 0 else 0

                    st.metric("💰 可借出金額 (再投入)", f"${max_loan:,}")
                    st.metric("📉 每月利息成本", f"- ${int(monthly_interest):,}")
                
                st.divider()
                res_c1, res_c2, res_c3 = st.columns(3)
                res_c1.metric("質押後總月領", f"${int(final_monthly_income):,}", delta=f"+${int(net_monthly_gain):,}")
                res_c2.metric("套利利差", f"{(yld - interest_rate):.2f}%")
                
                if maintenance_ratio < 130:
                    res_c3.error(f"維持率: {maintenance_ratio:.0f}% (危險)")
                elif maintenance_ratio < 160:
                    res_c3.warning(f"維持率: {maintenance_ratio:.0f}% (注意)")
                else:
                    res_c3.success(f"維持率: {maintenance_ratio:.0f}% (安全)")
        else:
            st.info("👈 請加入股票")
