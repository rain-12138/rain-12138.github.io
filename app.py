import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="基金估值监控看板", layout="wide")

st.title("📈 基金实时估值监控自选看板")

# 设置自选基金池
DEFAULT_FUNDS = ["005827", "161725", "001594", "011043"]

@st.cache_data(ttl=60) # 每60秒缓存失效，重新拉取
def get_fund_data():
    df = ak.fund_value_estimate_em()
    return df

try:
    with st.spinner('正在获取实时数据...'):
        all_data = get_fund_data()
        
    # 筛选自选基金
    my_funds = all_data[all_data['基金代码'].isin(DEFAULT_FUNDS)].copy()
    
    # 转换数据类型以便绘图
    my_funds['估算涨跌幅'] = pd.to_numeric(my_funds['估算涨跌幅'], errors='coerce')

    # --- 布局：上方显示核心指标卡片 ---
    cols = st.columns(len(my_funds))
    for i, row in enumerate(my_funds.itertuples()):
        cols[i].metric(
            label=row.基金名称, 
            value=row.实时估值, 
            delta=f"{row.估算涨跌幅}%"
        )

    # --- 布局：下方显示对比图表 ---
    st.divider()
    fig = px.bar(
        my_funds, 
        x='基金名称', 
        y='估算涨跌幅', 
        title="今日领涨/领跌对比 (%)",
        color='估算涨跌幅',
        color_continuous_scale='RdBu_r' # 红涨绿跌配色
    )
    st.plotly_chart(fig, use_container_width=True)

    # 显示原始数据表格
    st.subheader("详细数据明细")
    st.dataframe(my_funds[['基金代码', '基金名称', '估值时间', '实时估值', '单位净值', '估算涨跌幅']], use_container_width=True)

except Exception as e:
    st.error(f"数据加载失败: {e}")
