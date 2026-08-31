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
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    header    { visibility: hidden; }
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: 100% !important;
    }
    .stApp { background: #1a0f00; overflow: hidden; }
    iframe { height: 100vh !important; border: none !important; }
    ::-webkit-scrollbar { display: none; }
    html, body { overflow: hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# ===== 读取并渲染停用页 HTML（带错误处理）=====
html_file = Path(__file__).parent / "index.html"

try:
    if not html_file.exists():
        # 文件不存在：列出当前目录内容帮助排查
        files = sorted(p.name for p in Path(__file__).parent.iterdir())
        st.error("❌ 找不到 index.html 文件")
        st.markdown(
            f"**当前目录**：`{html_file.parent}`  \n"
            f"**目录中的文件**：{', '.join(files) if files else '(空)'}"
        )
        st.info(
            "请确认 index.html 已和 app.py 一起上传到 GitHub 仓库根目录。\n\n"
            "三个文件必须在同一目录：\n"
            "- app.py\n"
            "- index.html\n"
            "- requirements.txt"
        )
    else:
        html_content = html_file.read_text(encoding="utf-8")
        st.components.v1.html(html_content, height=2000, scrolling=False)

except Exception as e:
    st.error(f"❌ 渲染失败：{type(e).__name__} — {e}")
    st.text(f"文件路径：{html_file}")
    st.info("请检查 index.html 是否完整、编码是否为 UTF-8。")

st.stop()
