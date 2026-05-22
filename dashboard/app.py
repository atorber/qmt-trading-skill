"""QMT Trading Skill 可视化仪表盘 — 入口页面 + 侧边栏连接配置（调用 QMT Bridge API）。"""

import streamlit as st
from _sidebar import render_sidebar

st.set_page_config(
    page_title="QMT Trading Skill 仪表盘",
    page_icon="📊",
    layout="wide",
)

render_sidebar()

# ── 首页内容 ──────────────────────────────────────────────────────

st.title("QMT Trading Skill 可视化仪表盘")

st.markdown("""
**QMT Trading Skill** 包含 **QMT Bridge**（miniQMT / xtquant 的 HTTP/WebSocket API）与 Agent Skills；本仪表盘连接 Bridge 服务，
让任意设备（Mac、Linux、手机）通过网络访问实时行情、历史数据和交易功能。

本仪表盘提供可视化界面，方便浏览行情数据、管理交易、查看系统状态。
""")

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("行情数据")
    st.markdown("K 线图、实时快照、大盘指数")
    st.page_link("pages/1_行情数据.py", label="前往 →")

    st.subheader("板块管理")
    st.markdown("板块列表、成分股查询")
    st.page_link("pages/2_板块管理.py", label="前往 →")

with col2:
    st.subheader("交易日历")
    st.markdown("交易日查询、日期校验、节假日")
    st.page_link("pages/3_交易日历.py", label="前往 →")

    st.subheader("合约信息")
    st.markdown("合约详情、指数权重、期权链、ETF")
    st.page_link("pages/4_合约信息.py", label="前往 →")

with col3:
    st.subheader("数据下载")
    st.markdown("批量下载、快捷下载")
    st.page_link("pages/5_数据下载.py", label="前往 →")

    st.subheader("交易管理")
    st.markdown("下单、撤单、持仓、资产")
    st.page_link("pages/6_交易管理.py", label="前往 →")

st.subheader("系统状态")
st.markdown("健康检查、版本信息、连接状态")
st.page_link("pages/7_系统状态.py", label="前往 →")

# ── 快速状态概览 ──────────────────────────────────────────────────

if st.session_state.get("connected"):
    st.markdown("---")
    st.subheader("快速概览")
    client = st.session_state["client"]
    try:
        c1, c2, c3 = st.columns(3)
        with c1:
            version = client.get_server_version()
            st.metric("服务端版本", version)
        with c2:
            xtdata_ver = client.get_xtdata_version()
            st.metric("xtquant 版本", xtdata_ver)
        with c3:
            status = client.get_connection_status()
            connected = status.get("connected", False) if isinstance(status, dict) else False
            st.metric("数据连接", "已连接" if connected else "未连接")
    except Exception as e:
        st.warning(f"获取概览信息失败: {e}")
