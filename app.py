# -*- coding: utf-8 -*-
"""
停用页入口
将 index.html 全屏渲染，隐藏所有 Streamlit 默认 UI。
部署：将 app.py + index.html + requirements.txt 推送到 GitHub，
      Streamlit Cloud 自动重启即完成部署。
"""

from pathlib import Path

import streamlit as st

# 页面配置：收起侧边栏，宽屏
st.set_page_config(
    page_title="本程序已停用",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ===== 隐藏 Streamlit 默认 UI，实现纯全屏效果 =====
st.markdown(
    """
<style>
    /* 隐藏右上角菜单、页脚、顶部栏 */
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    header    { visibility: hidden; }

    /* 内容区去边距、占满宽度 */
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: 100% !important;
    }

    /* 应用背景与隐藏滚动 */
    .stApp {
        background: #1a0f00;
        overflow: hidden;
    }

    /* iframe 占满视口 */
    iframe {
        height: 100vh !important;
        border: none !important;
    }

    /* 全局隐藏滚动条 */
    ::-webkit-scrollbar { display: none; }
    html, body { overflow: hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# ===== 读取并渲染停用页 HTML =====
html_file = Path(__file__).parent / "index.html"
html_content = html_file.read_text(encoding="utf-8")

# 全屏渲染（height 设较大值配合 CSS 100vh 覆盖）
st.components.v1.html(html_content, height=2000, scrolling=False)

# 停止执行后续代码（本文件为入口，后续无内容）
st.stop()
