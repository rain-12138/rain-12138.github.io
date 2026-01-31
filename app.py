import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. 页面基础配置
st.set_page_config(page_title="基金监控看板", layout="wide", page_icon="📊")

# 2. 增强型数据获取函数
@st.cache_data(ttl=300)
def get_safe_data():
    try:
        # 获取东方财富-开放式基金实时行情
        df = ak.fund_open_fund_daily_em()
        
        # 打印列名到后台日志，方便调试
        # print(df.columns.tolist()) 
        
        # 动态映射字典：兼容不同版本的 AKShare 列名
        mapping = {
            '基金代码': 'code',
            '基金简称': 'name',
            '单位净值': 'nav',
            '日增长率': 'change',
            '更新日期': 'date'
        }
        
        # 只重命名存在的列
        existing_mapping = {k: v for k, v in mapping.items() if k in df.columns}
        df = df.rename(columns=existing_mapping)
        
        # 关键步骤：确保核心列存在，如果不存在则找备用列名
        if 'nav' not in df.columns and '单位净值' in df.columns:
             df['nav'] = df['单位净值']
        
        # 强制转换数值，无法转换的变为 NaN
        df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
        df['change'] = pd.to_numeric(df['change'], errors='coerce')
        
        # 剔除 nav 或 change 为空的行
        df = df.dropna(subset=['nav', 'code'])
        
        return df
    except Exception as e:
        st.error(f"核心数据解析失败: {e}")
        return None

# 3. 主页面布局
all_data = get_safe_data()

if all_data is not None:
    st.title("📈 基金实时行情监控")
    
    # 侧边栏交互
    available_codes = all_data['code'].astype(str).tolist()
    default_selection = ["005827", "161725", "011043", "001594"]
    
    selected_codes = st.sidebar.multiselect(
        "选择或输入基金代码:",
        options=available_codes,
        default=[c for c in default_selection if c in available_codes]
    )

    if selected_codes:
        # 过滤数据
        subset = all_data[all_data['code'].isin(selected_codes)].copy()
        
        # 指标卡片
        cols = st.columns(len(subset))
        for i, row in enumerate(subset.itertuples()):
            # 处理涨跌幅显示
            change_val = row.change if pd.notnull(row.change) else 0.0
            cols[i].metric(
                label=row.name,
                value=f"¥{row.nav:.4f}",
                delta=f"{change_val}%"
            )

        # 图表展示
        st.divider()
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("涨跌幅对比")
            fig = px.bar(
                subset, 
                x='name', 
                y='change',
                color='change',
                color_continuous_scale=['#00ad11', '#eeeeee', '#ff0000'],
                range_color=[-3, 3]
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("详情明细")
            # 整理展示用的表格
            show_df = subset[['code', 'name', 'nav', 'change']].copy()
            show_df.columns = ['代码', '名称', '净值', '涨幅%']
            st.dataframe(show_df, hide_index=True, use_container_width=True)
            
    else:
        st.info("💡 请在左侧侧边栏搜索并选择基金（如输入 005827）。")
else:
    st.warning("⚠️ 接口响应异常。请尝试点击左侧刷新按钮，或检查网络连接。")

st.caption(f"数据源：AKShare | 最后同步：{datetime.now().strftime('%H:%M:%S')}")
