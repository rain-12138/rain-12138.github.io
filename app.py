import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. 页面基础配置
st.set_page_config(page_title="基金监控看板", layout="wide", page_icon="📊")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="metric-container"] {
        background-color: white;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# 2. 数据获取逻辑
@st.cache_data(ttl=300) # 缓存5分钟，避免频繁请求被封
def get_safe_data():
    try:
        # 获取东方财富-开放式基金实时行情
        df = ak.fund_open_fund_daily_em()
        
        # 统一字段名映射（适配不同版本的 AKShare）
        column_map = {
            '基金代码': 'code',
            '基金简称': 'name',
            '单位净值': 'nav',
            '日增长率': 'change',
            '更新日期': 'date'
        }
        df = df.rename(columns=column_map)
        
        # 清洗数据：转为数值型，处理百分号
        df['change'] = pd.to_numeric(df['change'], errors='coerce')
        df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
        
        # 只保留必要的列
        return df[['code', 'name', 'nav', 'change', 'date']]
    except Exception as e:
        st.error(f"数据抓取失败: {e}")
        return None

# 3. 侧边栏交互
st.sidebar.header("📊 监控配置")
with st.sidebar:
    st.write("数据源：东方财富 (天天基金)")
    refresh = st.button("🔄 手动刷新数据")
    if refresh:
        st.cache_data.clear()

# 4. 主页面逻辑
all_data = get_safe_data()

if all_data is not None:
    st.title("📈 基金实时行情监控")
    
    # 自选基金设置 (预设了一些常见基金)
    default_selection = ["005827", "161725", "011043", "001594"]
    available_codes = all_data['code'].tolist()
    
    selected_codes = st.sidebar.multiselect(
        "选择或输入基金代码:",
        options=available_codes,
        default=[c for c in default_selection if c in available_codes]
    )

    if selected_codes:
        # 过滤出自选基金
        subset = all_data[all_data['code'].isin(selected_codes)].copy()
        
        # --- 顶部卡片展示 ---
        cols = st.columns(len(subset))
        for i, row in enumerate(subset.itertuples()):
            cols[i].metric(
                label=row.name,
                value=f"¥{row.nav:.4f}",
                delta=f"{row.change}%"
            )

        # --- 图表展示 ---
        st.divider()
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("涨跌幅对比")
            # 绘图：红涨绿跌
            fig = px.bar(
                subset, 
                x='name', 
                y='change',
                color='change',
                color_continuous_scale=['#00ad11', '#eeeeee', '#ff0000'], # 绿-白-红
                range_color=[-3, 3],
                labels={'change': '涨跌幅 (%)', 'name': '基金名称'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("详情明细")
            st.dataframe(
                subset[['code', 'name', 'nav', 'change']],
                hide_index=True,
                use_container_width=True
            )
            
        # --- 市场行情排行 ---
        st.divider()
        with st.expander("🔥 查看今日市场涨幅榜 Top 10"):
            top_10 = all_data.sort_values('change', ascending=False).head(10)
            st.table(top_10[['code', 'name', 'nav', 'change']])
            
    else:
        st.info("💡 请在左侧侧边栏选择您想要监控的基金。")

    st.caption(f"注：数据来自公开网络接口，最后同步时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.warning("⚠️ 无法获取行情数据，可能是由于接口暂时受到限制，请稍后再试。")
