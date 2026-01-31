import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. 页面配置
st.set_page_config(page_title="基金监控看板", layout="wide")

# 2. 时区处理：将服务器 UTC 时间转为北京时间
def get_beijing_time():
    return datetime.utcnow() + timedelta(hours=8)

# 3. 增强版数据抓取
@st.cache_data(ttl=300)
def get_safe_data():
    try:
        # 获取数据
        df = ak.fund_open_fund_daily_em()
        
        # --- 模糊匹配列名，彻底解决 KeyError ---
        # 我们通过关键词来定位列，而不是死磕完整的列名
        col_map = {}
        for col in df.columns:
            if '代码' in col: col_map[col] = 'code'
            elif '简称' in col: col_map[col] = 'name'
            elif '单位净值' in col: col_map[col] = 'nav'
            elif '日增长率' in col: col_map[col] = 'change'
        
        df = df.rename(columns=col_map)
        
        # 只保留我们识别出来的列
        needed_cols = ['code', 'name', 'nav', 'change']
        # 检查是否所有列都找齐了
        if not all(c in df.columns for c in needed_cols):
            st.error(f"字段识别不全，当前识别到: {list(df.columns)}")
            return None

        # 数据清洗
        df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
        df['change'] = pd.to_numeric(df['change'], errors='coerce')
        df['code'] = df['code'].astype(str)
        
        return df[needed_cols].dropna(subset=['nav'])
    except Exception as e:
        st.error(f"接口调用异常: {e}")
        return None

# 4. 界面逻辑
all_data = get_safe_data()

if all_data is not None:
    st.title("📈 基金实时行情监控")
    
    # 侧边栏
    with st.sidebar:
        st.header("设置")
        if st.button("🔄 刷新数据"):
            st.cache_data.clear()
            st.rerun()
        
        available_codes = all_data['code'].tolist()
        default_codes = ["005827", "161725", "011043", "001594"]
        selected = st.multiselect(
            "选择基金代码:", 
            options=available_codes,
            default=[c for c in default_codes if c in available_codes]
        )

    if selected:
        subset = all_data[all_data['code'].isin(selected)]
        
        # 卡片展示
        cols = st.columns(len(subset))
        for i, row in enumerate(subset.itertuples()):
            cols[i].metric(
                label=row.name,
                value=f"{row.nav:.4f}",
                delta=f"{row.change}%"
            )
        
        # 柱状图
        st.divider()
        fig = px.bar(subset, x='name', y='change', color='change',
                     color_continuous_scale=['#00ad11', '#eeeeee', '#ff0000'],
                     range_color=[-3, 3], title="今日涨跌幅对比 (%)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("请在左侧搜索并选择基金代码。")

# 页脚显示北京时间
bj_time = get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"数据来源: AKShare | 北京时间: {bj_time} (服务器已自动校准)")
