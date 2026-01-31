import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

# 1. 页面全局配置
st.set_page_config(page_title="基金实时监控(带日志)", layout="wide", page_icon="⚡")

# 初始化日志存储
if 'runtime_logs' not in st.session_state:
    st.session_state.runtime_logs = []

def add_log(msg, level="INFO"):
    """记录运行日志"""
    now = (datetime.utcnow() + timedelta(hours=8)).strftime('%H:%M:%S')
    icon = "🔵" if level == "INFO" else "⚠️"
    st.session_state.runtime_logs.append(f"{icon} [{now}] {msg}")
    # 保持日志长度，只保留最近30条
    if len(st.session_state.runtime_logs) > 30:
        st.session_state.runtime_logs.pop(0)

def get_beijing_time():
    return datetime.utcnow() + timedelta(hours=8)

def is_market_open():
    now = get_beijing_time()
    if now.weekday() >= 5: return False
    curr = now.time()
    return (time(9,30) <= curr <= time(11,30)) or (time(13,0) <= curr <= time(15,0))

# 2. 强力数据解析引擎
def robust_parse(df, is_open):
    try:
        cols = df.columns.tolist()
        add_log(f"开始解析字段，列名清单: {cols[:5]}...")
        
        # 模糊匹配索引
        code_idx = next(i for i, c in enumerate(cols) if '代码' in c)
        name_idx = next(i for i, c in enumerate(cols) if '简称' in c or '名称' in c)
        
        if is_open:
            nav_idx = next(i for i, c in enumerate(cols) if '估值' in c)
            change_idx = next(i for i, c in enumerate(cols) if '涨跌' in c)
        else:
            nav_idx = next(i for i, c in enumerate(cols) if '单位净值' in c)
            change_idx = next(i for i, c in enumerate(cols) if '增长率' in c)

        add_log(f"字段定位成功: 代码[{code_idx}], 名称[{name_idx}], 数值[{nav_idx}], 涨跌[{change_idx}]")

        clean_df = pd.DataFrame({
            'code': df.iloc[:, code_idx].astype(str),
            'name': df.iloc[:, name_idx].astype(str),
            'nav': pd.to_numeric(df.iloc[:, nav_idx], errors='coerce'),
            'change': pd.to_numeric(df.iloc[:, change_idx], errors='coerce')
        })
        res = clean_df.dropna(subset=['nav'])
        add_log(f"数据清洗完成，有效行数: {len(res)}")
        return res
    except Exception as e:
        add_log(f"解析失败: {str(e)}", "WARN")
        return None

# 3. 数据拉取与缓存
@st.cache_data(ttl=60)
def fetch_data(is_open):
    try:
        if is_open:
            add_log("检测到开盘时段，请求 [实时估值] 接口...")
            raw = ak.fund_value_estimate_em()
            mode = "🔴 盘中实时估值"
        else:
            add_log("检测到休市时段，请求 [每日净值] 接口...")
            raw = ak.fund_open_fund_daily_em()
            mode = "⚪ 非交易时段(昨日净值)"
        
        processed = robust_parse(raw, is_open)
        return processed, mode
    except Exception as e:
        add_log(f"接口请求异常: {str(e)}", "WARN")
        return None, f"异常: {e}"

# --- 4. 界面展示 ---
bj_now = get_beijing_time()
market_status = is_market_open()

st.title("📈 基金监控与运行诊断系统")

# 侧边栏：监控配置与日志开关
with st.sidebar:
    st.header("⚙️ 系统控制")
    show_logs = st.checkbox("展示运行日志", value=True)
    if st.button("🚀 刷新数据并清空日志"):
        st.cache_data.clear()
        st.session_state.runtime_logs = []
        st.rerun()
    
    st.divider()
    st.info(f"北京时间: {bj_now.strftime('%H:%M:%S')}\n\n市场状态: {'交易中' if market_status else '休市'}")

# 执行抓取
all_data, data_mode = fetch_data(market_status)

# 布局：左侧主看板，右侧日志(如果开启)
col_main, col_log = st.columns([3, 1]) if show_logs else (st.container(), None)

with col_main:
    if all_data is not None:
        available_codes = all_data['code'].tolist()
        selected_codes = st.multiselect("添加基金代码:", options=available_codes, default=[c for c in ["005827", "161725"] if c in available_codes])

        if selected_codes:
            subset = all_data[all_data['code'].isin(selected_codes)]
            
            # 指标卡
            card_cols = st.columns(min(len(subset), 3) if len(subset) > 0 else 1)
            for i, row in enumerate(subset.itertuples()):
                card_cols[i % 3].metric(label=row.name, value=f"{row.nav:.4f}", delta=f"{row.change}%")
            
            # 图表
            st.divider()
            fig = px.bar(subset, x='name', y='change', color='change',
                         color_continuous_scale=['#098154', '#f1f1f1', '#cf1020'],
                         range_color=[-3, 3], title=f"行情分布 ({data_mode})")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("💡 请输入并选择基金代码进行监控。")
    else:
        st.error("数据抓取失败，请检查右侧日志。")

# 右侧日志面板
if show_logs and col_log:
    with col_log:
        st.subheader("📝 运行日志")
        log_container = st.container(height=500)
        with log_container:
            if st.session_state.runtime_logs:
                for log in reversed(st.session_state.runtime_logs): # 最新日志在最上面
                    st.caption(log)
            else:
                st.write("等待数据加载...")

st.caption("数据源: AKShare / 天天基金 | 仅供参考，不构成投资建议")
