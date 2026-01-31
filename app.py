import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. 基础配置
st.set_page_config(page_title="基金实时估值助手", layout="wide", page_icon="📈")

# 自定义 CSS 让表格和卡片更好看
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# 2. 标题和侧边栏
st.title("🚀 基金实时估值监控看板")
st.sidebar.header("配置参数")
refresh_btn = st.sidebar.button("立即刷新数据")

# 3. 数据获取函数 (增加缓存防止频繁请求被封)
@st.cache_data(ttl=60)  # 缓存1分钟
def fetch_data():
    try:
        df = ak.fund_value_estimate_em()
        # 转换数值型字段
        df['实时估值'] = pd.to_numeric(df['实时估值'], errors='coerce')
        df['估算涨跌幅'] = pd.to_numeric(df['估算涨跌幅'], errors='coerce')
        df['单位净值'] = pd.to_numeric(df['单位净值'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"获取数据失败: {e}")
        return None

# 4. 执行获取数据
with st.spinner('正在同步天天基金实时数据...'):
    all_data = fetch_data()

if all_data is not None:
    # 侧边栏：自选基金功能
    fund_list = all_data['基金代码'].tolist()
    default_list = ["005827", "161725", "011043", "001594"] # 预设几个热门基金
    
    selected_codes = st.sidebar.multiselect(
        "搜索并选择你的自选基金:",
        options=fund_list,
        default=[code for code in default_list if code in fund_list]
    )

    # 5. 核心逻辑：数据展示
    if selected_codes:
        my_funds = all_data[all_data['基金代码'].isin(selected_codes)].copy()
        
        # --- 第一部分：指标卡片 ---
        st.subheader("📌 自选基金盘中表现")
        cols = st.columns(len(my_funds))
        for i, row in enumerate(my_funds.itertuples()):
            color = "normal" if row.估算涨跌幅 >= 0 else "inverse"
            cols[i].metric(
                label=row.基金名称,
                value=f"{row.实时估值:.4f}",
                delta=f"{row.估算涨跌幅}%"
            )

        # --- 第二部分：可视化图表 ---
        st.divider()
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.write("📊 **涨跌幅对比图**")
            fig = px.bar(
                my_funds, 
                x='基金名称', 
                y='估算涨跌幅',
                color='估算涨跌幅',
                color_continuous_scale='RdBu_r',
                range_color=[-3, 3]
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.write("📋 **详细行情明细**")
            st.dataframe(
                my_funds[['基金代码', '基金名称', '实时估值', '估算涨跌幅', '估值时间']],
                hide_index=True,
                use_container_width=True
            )

        # --- 第三部分：全市场概览 (可选展示) ---
        with st.expander("🔍 查看全市场基金估值 Top 10 (按涨幅)"):
            top_10 = all_data.sort_values('估算涨跌幅', ascending=False).head(10)
            st.table(top_10[['基金代码', '基金名称', '估算涨跌幅', '实时估值']])

    else:
        st.warning("请在左侧边栏搜索并选择基金代码以进行监控。")

    # 页脚
    st.caption(f"数据更新于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (每分钟自动同步一次)")
else:
    st.error("无法加载基金数据，请检查网络或稍后再试。")
