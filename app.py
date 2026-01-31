import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. 页面配置
st.set_page_config(page_title="基金监控(测试版)", layout="wide")

# 北京时间校准
def get_beijing_time():
    return datetime.utcnow() + timedelta(hours=8)

# 2. 调试信息打印组件
def log_debug(message, data=None):
    if 'debug_logs' not in st.session_state:
        st.session_state.debug_logs = []
    timestamp = get_beijing_time().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    st.session_state.debug_logs.append(log_entry)
    if data is not None:
        st.session_state.debug_logs.append(f"   ﹂ Data Preview: {str(data)}")

# 3. 增强型抓取函数
@st.cache_data(ttl=60)
def get_data_with_debug():
    try:
        log_debug("开始调用 ak.fund_open_fund_daily_em()...")
        df_raw = ak.fund_open_fund_daily_em()
        
        # 记录原始列名
        log_debug("接口返回成功", f"列名: {df_raw.columns.tolist()[:10]}... (共{len(df_raw.columns)}列)")
        log_debug(f"原始数据行数: {len(df_raw)}")

        # 模糊匹配列名
        log_debug("正在匹配关键列名...")
        code_col = [c for c in df_raw.columns if '代码' in c][0]
        name_col = [c for c in df_raw.columns if '简称' in c][0]
        nav_col = [c for c in df_raw.columns if '单位净值' in c][0]
        change_col = [c for c in df_raw.columns if '日增长率' in c][0]

        # 抽取数据并处理多维情况
        def ensure_1d(series_or_df):
            if isinstance(series_or_df, pd.DataFrame):
                return series_or_df.iloc[:, 0]
            return series_or_df

        log_debug("正在进行数据类型转换和清洗...")
        data = pd.DataFrame({
            'code': ensure_1d(df_raw[code_col]).astype(str),
            'name': ensure_1d(df_raw[name_col]).astype(str),
            'nav': pd.to_numeric(ensure_1d(df_raw[nav_col]), errors='coerce'),
            'change': pd.to_numeric(ensure_1d(df_raw[change_col]), errors='coerce')
        })

        clean_data = data.dropna(subset=['nav', 'code'])
        log_debug(f"清洗完成，可用数据行数: {len(clean_data)}")
        
        return clean_data

    except Exception as e:
        log_debug(f"🛑 发生异常: {str(e)}")
        st.error(f"解析失败，请查看下方运行记录。错误类型: {type(e).__name__}")
        return None

# --- UI 布局 ---
st.title("📊 基金数据监控 - 测试环境")

# 侧边栏：控制台开关
with st.sidebar:
    show_debug = st.checkbox("显示运行记录 (Debug Logs)", value=True)
    if st.button("🚀 强制重试"):
        st.cache_data.clear()
        st.session_state.debug_logs = []
        st.rerun()

# 获取数据
all_data = get_data_with_debug()

# 主展示区
if all_data is not None:
    # 基金选择
    codes = all_data['code'].tolist()
    selected = st.multiselect("🔍 搜索并选择监控基金:", codes, default=[c for c in ["005827", "161725"] if c in codes])

    if selected:
        subset = all_data[all_data['code'].isin(selected)]
        
        # 卡片
        c_list = st.columns(len(subset) if len(subset) > 0 else 1)
        for i, row in enumerate(subset.itertuples()):
            c_list[i].metric(row.name, f"{row.nav:.4f}", f"{row.change}%")
        
        # 详细数据表
        st.write("### 选定基金明细")
        st.table(subset)
    else:
        st.info("请选择基金代码进行预览。")

# --- 运行记录面板 ---
if show_debug:
    st.divider()
    with st.expander("📝 运行记录 / 调试控制台", expanded=True):
        if 'debug_logs' in st.session_state:
            for log in st.session_state.debug_logs:
                st.code(log)
        else:
            st.write("暂无运行记录")

st.caption(f"北京时间: {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}")
