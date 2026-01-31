import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

# 1. 页面配置
st.set_page_config(page_title="基金实时估值系统", layout="wide", page_icon="⚡")

# 2. 工具函数：判断是否为开盘时间
def is_market_open():
    now = datetime.utcnow() + timedelta(hours=8) # 转北京时间
    # 周六日不交易
    if now.weekday() >= 5:
        return False
    
    current_time = now.time()
    # 上午 09:30 - 11:30
    morn_start, morn_end = time(9, 30), time(11, 30)
    # 下午 13:00 - 15:00
    aft_start, aft_end = time(13, 0), time(15, 0)
    
    is_morn = morn_start <= current_time <= morn_end
    is_aft = aft_start <= current_time <= aft_end
    
    return is_morn or is_aft

def get_beijing_time():
    return datetime.utcnow() + timedelta(hours=8)

# 3. 数据获取函数
@st.cache_data(ttl=60) # 交易期间每分钟刷新一次
def fetch_fund_data(is_open):
    try:
        if is_open:
            # --- 开盘期间：抓取实时估值接口 ---
            df = ak.fund_value_estimate_em()
            # 映射列名：代码, 名称, 实时估值, 估算涨跌幅
            df = df.rename(columns={
                '基金代码': 'code',
                '基金名称': 'name',
                '实时估值': 'nav',
                '估算涨跌幅': 'change'
            })
            status_text = "🔴 盘中实时估值"
        else:
            # --- 收盘/周末：抓取每日净值接口 ---
            df = ak.fund_open_fund_daily_em()
            df = df.rename(columns={
                '基金代码': 'code',
                '基金简称': 'name',
                '单位净值': 'nav',
                '日增长率': 'change'
            })
            status_text = "⚪ 非交易时段(昨日净值)"

        # 数据清洗
        def ensure_1d(s):
            return s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s

        clean_df = pd.DataFrame({
            'code': ensure_1d(df['code']).astype(str),
            'name': ensure_1d(df['name']).astype(str),
            'nav': pd.to_numeric(ensure_1d(df['nav']), errors='coerce'),
            'change': pd.to_numeric(ensure_1d(df['change']), errors='coerce')
        })
        return clean_df.dropna(subset=['nav']), status_text
    except Exception as e:
        st.error(f"获取失败: {e}")
        return None, "Error"

# --- UI 界面 ---
bj_now = get_beijing_time()
market_status = is_market_open()

st.title("📊 基金净值/估值监控")

# 显示当前市场状态
status_color = "red" if market_status else "gray"
st.markdown(f"**当前状态：** :{status_color}[{'交易中' if market_status else '已休市'}] | **北京时间：** {bj_now.strftime('%H:%M:%S')}")

all_data, data_mode = fetch_fund_data(market_status)

if all_data is not None:
    with st.sidebar:
        st.header("监控配置")
        st.info(f"模式: {data_mode}")
        if st.button("强制刷新"):
            st.cache_data.clear()
            st.rerun()
        
        codes = all_data['code'].tolist()
        selected = st.multiselect("选择基金:", codes, default=[c for c in ["005827", "161725"] if c in codes])

    if selected:
        subset = all_data[all_data['code'].isin(selected)]
        
        # 指标卡片
        cols = st.columns(len(subset) if len(subset) > 0 else 1)
        for i, row in enumerate(subset.itertuples()):
            cols[i].metric(
                label=row.name,
                value=f"{row.nav:.4f}",
                delta=f"{row.change}%"
            )
        
        # 可视化对比
        st.divider()
        fig = px.bar(
            subset, x='name', y='change', color='change',
            color_continuous_scale=['#098154', '#f1f1f1', '#cf1020'],
            range_color=[-3, 3],
            title=f"实时涨跌分布 ({data_mode})"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.table(subset)
    else:
        st.info("请在左侧选择基金。")
else:
    st.error("无法获取数据。")

st.caption(f"注：盘中估值仅供参考，实际净值以基金公司晚间公布为准。")
