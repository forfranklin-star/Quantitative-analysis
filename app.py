# -*- coding: utf-8 -*-
"""
停用页入口
- 将 index.html 全屏渲染，隐藏所有 Streamlit 默认 UI
- 内置定时自动运行：每日 08:00 / 16:00 / 24:00(即00:00) 自动重新运行一次

部署：将 app.py + index.html + requirements.txt 推送到 GitHub，
      Streamlit Cloud 检测到更新后自动重启即完成部署。

注意：Streamlit Cloud 免费应用在长时间无人访问时会休眠，休眠时代码内
      定时不会触发。若需要准点唤醒休眠中的应用，请配合外部定时访问服务
      （如 cron-job.org）在 08:00/16:00/00:00 访问一次本应用网址。
"""

import datetime as dt
from datetime import timedelta
from pathlib import Path

import streamlit as st

# ====================== 定时运行配置 ======================
# 每日自动运行的时间点（24 小时制，24 点写作 0）
RUN_HOURS = (0, 8, 16)
# 后台检查间隔：每 20 秒检查一次当前是否到达运行时间点
CHECK_INTERVAL = timedelta(seconds=20)
# 触发窗口：到达整点后 40 秒内都允许触发（覆盖至少两次检查，防止漏触发）
TRIGGER_WINDOW = timedelta(seconds=40)


def next_run_time(now: dt.datetime) -> dt.datetime:
    """计算 now 之后最近的一个计划运行时间点。"""
    candidates = []
    for offset in (0, 1):  # 今天、明天
        day = now + timedelta(days=offset)
        for hour in RUN_HOURS:
            candidates.append(
                day.replace(hour=hour, minute=0, second=0, microsecond=0)
            )
    return min(t for t in candidates if t > now)


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
    /* 定时调度 fragment 不占用任何可见空间 */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stFragment"]) {
        display: none;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ====================== 定时调度器 ======================
# 记录上一次已触发的时间点（格式 YYYYMMDDHH），避免同一整点重复运行
if "last_trigger_key" not in st.session_state:
    st.session_state.last_trigger_key = None


@st.fragment(run_every=CHECK_INTERVAL)
def auto_scheduler():
    """后台静默运行：到达 08:00/16:00/00:00 时整页重新运行一次。"""
    now = dt.datetime.now()
    for hour in RUN_HOURS:
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        gap = (now - target).total_seconds()
        if 0 <= gap <= TRIGGER_WINDOW.total_seconds():
            trigger_key = target.strftime("%Y%m%d%H")
            if st.session_state.last_trigger_key != trigger_key:
                st.session_state.last_trigger_key = trigger_key
                print(
                    f"[scheduler] 定时触发 @ {target:%Y-%m-%d %H:%M}，"
                    f"自动重新运行应用",
                    flush=True,
                )
                # scope="app"：重新运行整个应用（而非仅本 fragment）
                st.rerun(scope="app")


# 启动后台调度（不输出任何可见内容）
auto_scheduler()

# 打印本次运行信息到云端日志，便于在 Streamlit Cloud 终端核对
_now = dt.datetime.now()
print(
    f"[scheduler] 应用运行 @ {_now:%Y-%m-%d %H:%M:%S}，"
    f"下次定时运行：{next_run_time(_now):%Y-%m-%d %H:%M}",
    flush=True,
)

# ====================== 渲染停用页 HTML ======================
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
        # Streamlit 新版（>=1.63）推荐 st.iframe；旧版本回退到 components.v1.html
        if hasattr(st, "iframe"):
            st.iframe(html_content, height=2000)
        else:
            st.components.v1.html(html_content, height=2000, scrolling=False)

except Exception as e:
    st.error(f"❌ 渲染失败：{type(e).__name__} — {e}")
    st.text(f"文件路径：{html_file}")
    st.info("请检查 index.html 是否完整、编码是否为 UTF-8。")

st.stop()
