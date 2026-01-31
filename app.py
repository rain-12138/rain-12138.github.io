import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. 页面配置
st.set_page_config(page_title="我的基金监控中心", layout="wide", page_icon="📈")

# 自定义样式：让数据卡片更醒目
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #1f77b4; }
    .main { background-color: #f9fbfd; }
    </style>
""", unsafe_allow_html=True)

def get_beijing_time():
    return datetime.utcnow() + timedelta(hours=8)

# 2. 高效数据抓取
@st.cache_data(ttl=300)
def get_final_data():
    try:
        df_raw = ak.fund_open_fund_daily_em()
        
        # 自动定位列
        code_col = [c for c in df_raw.columns if '代码' in c][0]
        name_col = [c for c in df_raw.columns if '简称' in c][0]
        nav_col = [c for c in df_raw.columns if '单位净值' in c][0]
        change_col = [c for c in df_raw.columns if '日增长率' in c][0]

        def ensure_1d(s):
            return s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s

        data = pd.DataFrame({
            '基金代码': ensure_1d(df_raw[code_col]).astype(str),
            '基金名称': ensure_1d(df_raw[name_col]).astype(str),
            '当前净值': pd.to_numeric(ensure_1d(df_raw[nav_col]), errors='coerce'),
            '今日涨跌%': pd.to_numeric(ensure_1d(df_raw[change_col]), errors='coerce')
        })
        return data.dropna(subset=['当前净值', '基金代码'])
    except:
        return None

# --- 执行区 ---
all_data = get_final_data()

if all_data is not None:
    st.title("🛡️ 我的基金实时监控中心")
    
    # 侧边栏
    with st.sidebar:
        st.subheader("⚙️ 监控设置")
        if st.button("🔄 刷新行情"):
            st.cache_data.clear()
            st.rerun()
        
        codes = all_data['基金代码'].tolist()
        # 这里你可以把你常用的代码填在 default 里
        selected = st.multiselect("添加自选基金:", codes, default=["005827", "161725", "001594"])

    if selected:
        subset = all_data[all_data['基金代码'].isin(selected)]
        
        # 第一排：核心数据指标卡
        st.subheader("💎 自选基金表现")
        # 自动计算列数，每行最多 4 个
        cols = st.columns(4)
        for i, row in enumerate(subset.itertuples()):
            with cols[i % 4]:
                st.metric(
                    label=row.基金名称, 
                    value=f"¥{row.当前净值:.4f}", 
                    delta=f"{row.今日涨跌%}%"
                )
        
        # 第二排：可视化分析
        st.divider()
        c1, c2 = st.columns([3, 2])
        
        with c1:
            st.write("📊 **涨跌幅实时对比**")
            fig = px.bar(
                subset, x='基金名称', y='今日涨跌%', color='今日涨跌%',
                color_continuous_scale=['#098154', '#f1f1f1', '#cf1020'], # 绿白红
                range_color=[-4, 4],
                text_auto='.2f'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.write("📋 **资产明细清单**")
            st.dataframe(
                subset, 
                column_config={"今日涨跌%": st.column_config.NumberColumn(format="%.2f%%")},
                hide_index=True, 
                use_container_width=True
            )
            
        # 第三排：市场趋势
        with st.expander("🔥 查看今日市场涨幅 Top 10"):
            top_10 = all_data.sort_values('今日涨跌%', ascending=False).head(10)
            st.table(top_10)

    else:
        st.info("💡 请在左侧侧边栏搜索并加入您的基金代码。")
else:
    st.error("数据源连接失败，请检查 AKShare 库版本。")

# 页脚
bj_now = get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"🏁 监控中 | 北京时间: {bj_now} | 数据由天天基金提供")
