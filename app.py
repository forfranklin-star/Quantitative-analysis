# -*- coding: utf-8 -*-
"""
A股量化策略分析器
==================
基于 Streamlit + AkShare + Plotly 的交互式股票量化分析与回测工具。

功能模块：
  1. 数据获取：AkShare 拉取 A 股前复权日线行情
  2. 指标计算：MA / MACD / RSI / KDJ / 布林带
  3. 策略信号：均线交叉 / MACD / RSI / 布林带 / 综合投票
  4. 回测引擎：T+1 次日开盘成交、全仓买卖、佣金+印花税+滑点
  5. 可视化：K线+副图、资金曲线、回撤曲线、交易明细

运行方式：
  pip install -r requirements.txt
  streamlit run app.py
"""

import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import akshare as ak
import streamlit as st
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")

# ============================================================
# 页面全局配置（必须在所有 st 命令之前调用）
# ============================================================
st.set_page_config(
    page_title="A股量化策略分析器",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 一、数据获取模块
# ============================================================
@st.cache_data(ttl=3600, show_spinner="正在从 AkShare 获取行情数据…")
def fetch_stock_data(symbol: str, start_date: str, end_date: str, adjust: str = "qfq"):
    """
    获取 A 股日线行情数据（前复权）。

    参数
    ----
    symbol : str
        6 位股票代码，如 "600519"
    start_date : str
        开始日期，格式 "YYYY-MM-DD"
    end_date : str
        结束日期，格式 "YYYY-MM-DD"
    adjust : str
        复权方式：qfq=前复权，hfq=后复权，""=不复权

    返回
    ----
    pd.DataFrame 或 None
        列：date, open, close, high, low, volume, amount, pct_chg
    """
    try:
        # AkShare 接口要求日期为 "YYYYMMDD" 格式
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust=adjust,
        )
        if df is None or df.empty:
            return None

        # 将 AkShare 返回的中文列名统一为英文
        df = df.rename(
            columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
                "涨跌幅": "pct_chg",
            }
        )
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df

    except Exception as e:
        st.error(f"❌ 数据获取失败：{type(e).__name__} — {e}")
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def get_stock_name(symbol: str) -> str:
    """根据股票代码查询股票名称，失败则返回代码本身。"""
    try:
        name_df = ak.stock_info_a_code_name()
        row = name_df[name_df["code"] == symbol]
        if not row.empty:
            return f"{symbol} {row.iloc[0]['name']}"
    except Exception:
        pass
    return symbol


# ============================================================
# 二、技术指标计算模块
# ============================================================
def calc_ma(df: pd.DataFrame, periods: list) -> pd.DataFrame:
    """计算简单移动平均线（MA）。"""
    for p in periods:
        df[f"MA{p}"] = df["close"].rolling(window=p, min_periods=1).mean()
    return df


def calc_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    计算 MACD 指标。
    DIF = EMA(fast) - EMA(slow)
    DEA = EMA(DIF, signal)
    MACD 柱 = 2 * (DIF - DEA)
    """
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    df["DIF"] = ema_fast - ema_slow
    df["DEA"] = df["DIF"].ewm(span=signal, adjust=False).mean()
    df["MACD"] = 2 * (df["DIF"] - df["DEA"])
    return df


def calc_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    计算 RSI（相对强弱指标），采用 Wilder 平滑法。
    """
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    # 初始均值用简单平均，后续用 Wilder 平滑（等价于 ewm alpha=1/period）
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["RSI"] = df["RSI"].fillna(50)  # 除零保护
    return df


def calc_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
    """
    计算 KDJ 指标。
    RSV = (close - low_n) / (high_n - low_n) * 100
    K = SMA(RSV, m1)，D = SMA(K, m2)，J = 3K - 2D
    """
    low_n = df["low"].rolling(window=n, min_periods=1).min()
    high_n = df["high"].rolling(window=n, min_periods=1).max()
    rsv = (df["close"] - low_n) / (high_n - low_n).replace(0, np.nan) * 100
    rsv = rsv.fillna(50)

    # ewm(com=m-1) 等价于 SMA 递推：K_t = (m-1)/m * K_{t-1} + 1/m * RSV_t
    df["K"] = rsv.ewm(com=m1 - 1, adjust=False).mean()
    df["D"] = df["K"].ewm(com=m2 - 1, adjust=False).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]
    return df


def calc_boll(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """
    计算布林带（BOLL）。
    中轨 = MA(period)，上轨 = 中轨 + std_dev * σ，下轨 = 中轨 - std_dev * σ
    """
    df["BOLL_MID"] = df["close"].rolling(window=period, min_periods=1).mean()
    std = df["close"].rolling(window=period, min_periods=1).std()
    df["BOLL_UP"] = df["BOLL_MID"] + std_dev * std
    df["BOLL_DN"] = df["BOLL_MID"] - std_dev * std
    return df


# ============================================================
# 三、策略信号生成模块
#   signal 列约定：1 = 买入信号，-1 = 卖出信号，0 = 无操作
# ============================================================
def gen_ma_cross_signal(df: pd.DataFrame, fast: int = 5, slow: int = 20) -> pd.DataFrame:
    """均线交叉策略：快线上穿慢线（金叉）买入，下穿（死叉）卖出。"""
    df["signal"] = 0
    fast_col, slow_col = f"MA{fast}", f"MA{slow}"
    if fast_col not in df.columns or slow_col not in df.columns:
        return df

    cross_up = (df[fast_col] > df[slow_col]) & (df[fast_col].shift(1) <= df[slow_col].shift(1))
    cross_down = (df[fast_col] < df[slow_col]) & (df[fast_col].shift(1) >= df[slow_col].shift(1))
    df.loc[cross_up, "signal"] = 1
    df.loc[cross_down, "signal"] = -1
    return df


def gen_macd_signal(df: pd.DataFrame) -> pd.DataFrame:
    """MACD 策略：DIF 上穿 DEA 买入，下穿卖出。"""
    df["signal"] = 0
    cross_up = (df["DIF"] > df["DEA"]) & (df["DIF"].shift(1) <= df["DEA"].shift(1))
    cross_down = (df["DIF"] < df["DEA"]) & (df["DIF"].shift(1) >= df["DEA"].shift(1))
    df.loc[cross_up, "signal"] = 1
    df.loc[cross_down, "signal"] = -1
    return df


def gen_rsi_signal(df: pd.DataFrame, oversold: int = 30, overbought: int = 70) -> pd.DataFrame:
    """RSI 策略：从超卖区上穿买入，从超买区下穿卖出。"""
    df["signal"] = 0
    buy = (df["RSI"] < oversold) & (df["RSI"].shift(1) >= oversold)
    sell = (df["RSI"] > overbought) & (df["RSI"].shift(1) <= overbought)
    df.loc[buy, "signal"] = 1
    df.loc[sell, "signal"] = -1
    return df


def gen_boll_signal(df: pd.DataFrame) -> pd.DataFrame:
    """布林带突破策略：收盘价跌破下轨买入，突破上轨卖出。"""
    df["signal"] = 0
    buy = (df["close"] < df["BOLL_DN"]) & (df["close"].shift(1) >= df["BOLL_DN"].shift(1))
    sell = (df["close"] > df["BOLL_UP"]) & (df["close"].shift(1) <= df["BOLL_UP"].shift(1))
    df.loc[buy, "signal"] = 1
    df.loc[sell, "signal"] = -1
    return df


def gen_composite_signal(
    df: pd.DataFrame,
    fast: int = 5,
    slow: int = 20,
    oversold: int = 30,
    overbought: int = 70,
) -> pd.DataFrame:
    """
    综合信号策略（多指标投票）：
    对 MA / MACD / RSI / BOLL 四个子策略分别计算信号，
    当日买入信号数 >= 2 则发出买入，卖出信号数 >= 2 则发出卖出。
    """
    idx = df.index

    # --- 子策略 1：均线交叉 ---
    sig_ma = pd.Series(0, index=idx)
    fc, sc = f"MA{fast}", f"MA{slow}"
    if fc in df.columns and sc in df.columns:
        sig_ma[(df[fc] > df[sc]) & (df[fc].shift(1) <= df[sc].shift(1))] = 1
        sig_ma[(df[fc] < df[sc]) & (df[fc].shift(1) >= df[sc].shift(1))] = -1

    # --- 子策略 2：MACD ---
    sig_macd = pd.Series(0, index=idx)
    sig_macd[(df["DIF"] > df["DEA"]) & (df["DIF"].shift(1) <= df["DEA"].shift(1))] = 1
    sig_macd[(df["DIF"] < df["DEA"]) & (df["DIF"].shift(1) >= df["DEA"].shift(1))] = -1

    # --- 子策略 3：RSI ---
    sig_rsi = pd.Series(0, index=idx)
    sig_rsi[(df["RSI"] < oversold) & (df["RSI"].shift(1) >= oversold)] = 1
    sig_rsi[(df["RSI"] > overbought) & (df["RSI"].shift(1) <= overbought)] = -1

    # --- 子策略 4：布林带 ---
    sig_boll = pd.Series(0, index=idx)
    sig_boll[(df["close"] < df["BOLL_DN"]) & (df["close"].shift(1) >= df["BOLL_DN"].shift(1))] = 1
    sig_boll[(df["close"] > df["BOLL_UP"]) & (df["close"].shift(1) <= df["BOLL_UP"].shift(1))] = -1

    # --- 投票 ---
    buy_count = sum((s == 1).astype(int) for s in [sig_ma, sig_macd, sig_rsi, sig_boll])
    sell_count = sum((s == -1).astype(int) for s in [sig_ma, sig_macd, sig_rsi, sig_boll])

    df["signal"] = 0
    df.loc[buy_count >= 2, "signal"] = 1
    df.loc[sell_count >= 2, "signal"] = -1
    return df


# ============================================================
# 四、回测引擎模块
# ============================================================
def backtest(
    df: pd.DataFrame,
    init_capital: float = 100000,
    commission_rate: float = 0.0003,
    stamp_tax: float = 0.001,
    slippage: float = 0.001,
):
    """
    事件驱动回测引擎。

    交易规则
    --------
    * T+1：当日产生信号，次日开盘价成交
    * 全仓买卖：买入时用全部可用资金，卖出时清仓
    * 100 股整数倍（A 股最小交易单位）
    * 费用模型：
        - 买入：佣金 = max(成交金额 * 佣金率, 5 元)
        - 卖出：佣金 + 印花税(成交金额 * 印花税率)
    * 滑点：买入价 = 开盘价 * (1 + 滑点)，卖出价 = 开盘价 * (1 - 滑点)
    * 回测结束时若仍有持仓，按最后一日收盘价清算

    返回
    ----
    (df, trades_df, metrics)
        df        : 追加 equity / drawdown 列的行情 DataFrame
        trades_df : 交易明细 DataFrame
        metrics   : 绩效指标字典
    """
    if df is None or df.empty or "signal" not in df.columns:
        return None, None, None

    capital = float(init_capital)
    position = 0  # 持仓股数
    trades = []
    equity_curve = []
    drawdowns = []
    peak = capital

    for i in range(len(df)):
        row = df.iloc[i]

        # 当日权益（持仓按收盘价盯市）
        equity = capital + position * row["close"] if position > 0 else capital
        equity_curve.append(equity)

        # 记录回撤
        peak = max(peak, equity)
        drawdowns.append((peak - equity) / peak if peak > 0 else 0)

        # 信号在次日开盘执行（最后一日无次日，跳过）
        if i >= len(df) - 1 or row["signal"] == 0:
            continue

        next_row = df.iloc[i + 1]
        exec_price = next_row["open"]

        # ---------- 买入 ----------
        if row["signal"] == 1 and position == 0:
            buy_price = exec_price * (1 + slippage)
            # 预留佣金后计算可买股数（100 股取整）
            max_shares = int(capital / (buy_price * (1 + commission_rate)) / 100) * 100
            if max_shares >= 100:
                cost = max_shares * buy_price
                commission = max(cost * commission_rate, 5.0)
                total_cost = cost + commission
                if total_cost <= capital:
                    capital -= total_cost
                    position = max_shares
                    trades.append(
                        {
                            "日期": next_row["date"].strftime("%Y-%m-%d"),
                            "方向": "买入",
                            "成交价": round(buy_price, 3),
                            "数量": max_shares,
                            "成交金额": round(cost, 2),
                            "佣金": round(commission, 2),
                            "印花税": 0.0,
                            "剩余资金": round(capital, 2),
                        }
                    )

        # ---------- 卖出 ----------
        elif row["signal"] == -1 and position > 0:
            sell_price = exec_price * (1 - slippage)
            revenue = position * sell_price
            commission = max(revenue * commission_rate, 5.0)
            tax = revenue * stamp_tax
            net = revenue - commission - tax
            capital += net
            trades.append(
                {
                    "日期": next_row["date"].strftime("%Y-%m-%d"),
                    "方向": "卖出",
                    "成交价": round(sell_price, 3),
                    "数量": position,
                    "成交金额": round(revenue, 2),
                    "佣金": round(commission, 2),
                    "印花税": round(tax, 2),
                    "剩余资金": round(capital, 2),
                }
            )
            position = 0

    # ---------- 期末清算 ----------
    if position > 0:
        last = df.iloc[-1]
        revenue = position * last["close"]
        commission = max(revenue * commission_rate, 5.0)
        tax = revenue * stamp_tax
        net = revenue - commission - tax
        capital += net
        trades.append(
            {
                "日期": last["date"].strftime("%Y-%m-%d"),
                "方向": "卖出(期末清算)",
                "成交价": round(last["close"], 3),
                "数量": position,
                "成交金额": round(revenue, 2),
                "佣金": round(commission, 2),
                "印花税": round(tax, 2),
                "剩余资金": round(capital, 2),
            }
        )
        position = 0
        equity_curve[-1] = capital

    df["equity"] = equity_curve
    df["drawdown"] = drawdowns

    # ---------- 绩效指标 ----------
    metrics = _calc_performance(df, init_capital, trades)
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    return df, trades_df, metrics


def _calc_performance(df: pd.DataFrame, init_capital: float, trades: list) -> dict:
    """计算回测绩效指标：总收益、年化、最大回撤、夏普、胜率、盈亏比。"""
    final_equity = df["equity"].iloc[-1]
    total_return = (final_equity - init_capital) / init_capital

    # 年化收益率（按自然日）
    days = (df["date"].iloc[-1] - df["date"].iloc[0]).days
    years = days / 365.25 if days > 0 else 1.0
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

    # 最大回撤
    max_drawdown = df["drawdown"].max()

    # 夏普比率（无风险利率按年化 3%）
    daily_ret = df["equity"].pct_change().dropna()
    if len(daily_ret) > 1 and daily_ret.std() > 0:
        sharpe = (daily_ret.mean() - 0.03 / 252) / daily_ret.std() * np.sqrt(252)
    else:
        sharpe = 0.0

    # 胜率 & 盈亏比（按完整买卖配对计算）
    wins, losses = [], []
    buy_list = [t for t in trades if t["方向"] == "买入"]
    sell_list = [t for t in trades if "卖出" in t["方向"]]
    for b, s in zip(buy_list, sell_list):
        buy_cost = b["成交金额"] + b["佣金"]
        sell_net = s["成交金额"] - s["佣金"] - s["印花税"]
        pnl = sell_net - buy_cost
        (wins if pnl > 0 else losses).append(pnl)

    total_round = len(wins) + len(losses)
    win_rate = len(wins) / total_round if total_round > 0 else 0.0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = abs(float(np.mean(losses))) if losses else 0.0
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
        "win_rate": win_rate,
        "profit_loss_ratio": profit_loss_ratio,
        "final_equity": final_equity,
        "total_trades": total_round,
    }


# ============================================================
# 五、绘图模块（Plotly 交互式图表）
# ============================================================
def plot_kline_with_indicators(df: pd.DataFrame, ma_periods: list) -> go.Figure:
    """
    绘制 5 行联动图：
      Row1: K线 + 均线 + 布林带 + 买卖信号
      Row2: 成交量
      Row3: MACD
      Row4: RSI
      Row5: KDJ
    """
    fig = make_subplots(
        rows=5,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.38, 0.14, 0.16, 0.16, 0.16],
        subplot_titles=("K线 / 均线 / 布林带 / 交易信号", "成交量", "MACD", "RSI", "KDJ"),
    )

    # ---------- Row 1: K线 ----------
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="K线",
            increasing_line_color="#ef5350",
            decreasing_line_color="#26a69a",
            increasing_fillcolor="#ef5350",
            decreasing_fillcolor="#26a69a",
        ),
        row=1,
        col=1,
    )

    # 均线
    ma_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8", "#DDA0DD"]
    for i, p in enumerate(ma_periods):
        col = f"MA{p}"
        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["date"], y=df[col], name=f"MA{p}",
                    line=dict(width=1.2, color=ma_colors[i % len(ma_colors)]),
                ),
                row=1, col=1,
            )

    # 布林带
    if "BOLL_UP" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"], y=df["BOLL_UP"], name="BOLL上轨",
                line=dict(width=1, color="#9c27b0", dash="dot"), opacity=0.7,
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df["date"], y=df["BOLL_DN"], name="BOLL下轨",
                line=dict(width=1, color="#9c27b0", dash="dot"), opacity=0.7,
                fill="tonexty", fillcolor="rgba(156,39,176,0.08)",
            ),
            row=1, col=1,
        )

    # 交易信号箭头
    buy_sig = df[df["signal"] == 1]
    sell_sig = df[df["signal"] == -1]
    if not buy_sig.empty:
        fig.add_trace(
            go.Scatter(
                x=buy_sig["date"], y=buy_sig["low"] * 0.97,
                mode="markers", name="买入信号",
                marker=dict(symbol="triangle-up", size=13, color="#ef5350", line=dict(width=1, color="#fff")),
            ),
            row=1, col=1,
        )
    if not sell_sig.empty:
        fig.add_trace(
            go.Scatter(
                x=sell_sig["date"], y=sell_sig["high"] * 1.03,
                mode="markers", name="卖出信号",
                marker=dict(symbol="triangle-down", size=13, color="#26a69a", line=dict(width=1, color="#fff")),
            ),
            row=1, col=1,
        )

    # ---------- Row 2: 成交量 ----------
    vol_colors = ["#ef5350" if c >= o else "#26a69a" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(
        go.Bar(x=df["date"], y=df["volume"], name="成交量", marker_color=vol_colors, opacity=0.8),
        row=2, col=1,
    )

    # ---------- Row 3: MACD ----------
    fig.add_trace(
        go.Bar(
            x=df["date"], y=df["MACD"], name="MACD柱",
            marker_color=["#ef5350" if v >= 0 else "#26a69a" for v in df["MACD"]],
        ),
        row=3, col=1,
    )
    fig.add_trace(go.Scatter(x=df["date"], y=df["DIF"], name="DIF", line=dict(width=1.2, color="#FF6B6B")), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["DEA"], name="DEA", line=dict(width=1.2, color="#4ECDC4")), row=3, col=1)

    # ---------- Row 4: RSI ----------
    fig.add_trace(go.Scatter(x=df["date"], y=df["RSI"], name="RSI", line=dict(width=1.2, color="#FFA726")), row=4, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", opacity=0.5, row=4, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", opacity=0.5, row=4, col=1)

    # ---------- Row 5: KDJ ----------
    fig.add_trace(go.Scatter(x=df["date"], y=df["K"], name="K", line=dict(width=1.2, color="#FF6B6B")), row=5, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["D"], name="D", line=dict(width=1.2, color="#4ECDC4")), row=5, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["J"], name="J", line=dict(width=1, color="#FFA726")), row=5, col=1)

    # 隐藏非交易日（周末/节假日）造成的空隙
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])

    fig.update_layout(
        height=1250,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1, font=dict(size=10)),
        margin=dict(l=10, r=10, t=50, b=10),
        template="plotly_white",
        hovermode="x unified",
    )
    return fig


def plot_equity_drawdown(df: pd.DataFrame, init_capital: float) -> go.Figure:
    """绘制资金曲线（上）与回撤曲线（下）。"""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("资金曲线（策略权益）", "回撤曲线"),
        row_heights=[0.6, 0.4],
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["equity"], name="策略权益",
            line=dict(width=1.5, color="#1976D2"),
            fill="tozeroy", fillcolor="rgba(25,118,210,0.1)",
        ),
        row=1, col=1,
    )
    fig.add_hline(y=init_capital, line_dash="dash", line_color="#999", opacity=0.6, row=1, col=1)

    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["drawdown"] * 100, name="回撤",
            line=dict(width=1.2, color="#ef5350"),
            fill="tozeroy", fillcolor="rgba(239,83,80,0.15)",
        ),
        row=2, col=1,
    )

    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(
        height=520, template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="权益 (元)", row=1, col=1)
    fig.update_yaxes(title_text="回撤 (%)", row=2, col=1)
    return fig


# ============================================================
# 六、Streamlit 主界面
# ============================================================
def main():
    st.title("📈 A股量化策略分析器")
    st.caption("AkShare 行情 · 技术指标 · 策略回测 · 交互式可视化")

    # ===================== 侧边栏参数 =====================
    with st.sidebar:
        st.header("⚙️ 参数设置")

        # --- 股票与日期 ---
        st.subheader("📊 股票与日期")
        symbol = st.text_input("股票代码", value="600519", help="输入 6 位 A 股代码，如 600519")
        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("开始日期", value=datetime(2023, 1, 1))
        with c2:
            end_date = st.date_input("结束日期", value=datetime.now())

        # --- 回测参数 ---
        st.subheader("💰 回测参数")
        init_capital = st.number_input("初始资金 (元)", value=100000, min_value=10000, step=10000)
        commission_rate = st.number_input("佣金费率", value=0.0003, format="%.4f", help="万三 = 0.0003")
        stamp_tax = st.number_input("印花税率", value=0.001, format="%.4f", help="仅卖出时收取，千一 = 0.001")
        slippage = st.number_input("滑点比例", value=0.001, format="%.4f", help="成交价偏离开盘价的比例")

        # --- 技术指标参数 ---
        st.subheader("📐 技术指标参数")
        ma_periods_str = st.text_input("均线周期 (逗号分隔)", value="5,10,20,60")
        cm1, cm2 = st.columns(2)
        with cm1:
            macd_fast = st.number_input("MACD 快线", value=12, min_value=2)
            macd_slow = st.number_input("MACD 慢线", value=26, min_value=3)
        with cm2:
            macd_signal = st.number_input("MACD 信号线", value=9, min_value=2)
        rsi_period = st.number_input("RSI 周期", value=14, min_value=2)
        cb1, cb2 = st.columns(2)
        with cb1:
            boll_period = st.number_input("布林带周期", value=20, min_value=2)
        with cb2:
            boll_std = st.number_input("布林带标准差", value=2.0, min_value=0.5, step=0.5)
        kdj_n = st.number_input("KDJ 周期 N", value=9, min_value=2)

        # --- 策略选择 ---
        st.subheader("🎯 策略选择")
        strategy = st.selectbox(
            "交易策略",
            ["均线交叉", "MACD金叉死叉", "RSI超买超卖", "布林带突破", "综合信号(多指标投票)"],
            index=0,
        )

        # 策略专属参数（仅在选中对应策略时显示）
        ma_fast, ma_slow = 5, 20
        rsi_oversold, rsi_overbought = 30, 70
        if strategy == "均线交叉":
            cs1, cs2 = st.columns(2)
            with cs1:
                ma_fast = st.number_input("快线周期", value=5, min_value=2)
            with cs2:
                ma_slow = st.number_input("慢线周期", value=20, min_value=3)
        elif strategy == "RSI超买超卖":
            cs1, cs2 = st.columns(2)
            with cs1:
                rsi_oversold = st.number_input("超卖阈值", value=30, min_value=1, max_value=50)
            with cs2:
                rsi_overbought = st.number_input("超买阈值", value=70, min_value=50, max_value=99)

        run_btn = st.button("🚀 运行分析", type="primary", use_container_width=True)

    # ===================== 主区域 =====================
    if not run_btn:
        st.info("👈 在左侧设置参数后，点击「运行分析」开始。")
        st.markdown(
            """
            ### 功能概览

            | 模块 | 说明 |
            |------|------|
            | **数据来源** | AkShare 获取 A 股前复权日线行情 |
            | **技术指标** | MA / MACD / RSI / KDJ / 布林带 (BOLL) |
            | **交易策略** | 均线交叉 · MACD · RSI · 布林带 · 综合投票 |
            | **回测规则** | T+1 次日开盘成交，全仓买卖，100 股整数倍 |
            | **费用模型** | 佣金（最低 5 元）+ 印花税（卖出）+ 滑点 |
            | **输出内容** | K线副图 · 绩效卡片 · 资金曲线 · 交易明细 CSV |

            > ⚠️ 本工具仅供学习研究，不构成任何投资建议。
            """
        )
        return

    # ---------- 参数校验 ----------
    symbol = symbol.strip()
    if not symbol.isdigit() or len(symbol) != 6:
        st.error("❌ 股票代码格式错误，请输入 6 位数字代码。")
        return
    if start_date >= end_date:
        st.error("❌ 开始日期必须早于结束日期。")
        return

    try:
        ma_periods = [int(x.strip()) for x in ma_periods_str.split(",") if x.strip()]
        if not ma_periods:
            raise ValueError
    except (ValueError, TypeError):
        st.error("❌ 均线周期格式错误，请用逗号分隔数字，如 5,10,20,60。")
        return

    # ---------- 1. 获取数据 ----------
    df = fetch_stock_data(symbol, str(start_date), str(end_date))
    if df is None or df.empty:
        st.error("❌ 未获取到数据，请检查股票代码是否正确、日期范围内是否有交易日。")
        return

    # 数据量预警
    min_required = max(ma_periods + [macd_slow, rsi_period, boll_period, kdj_n]) + 5
    if len(df) < min_required:
        st.warning(
            f"⚠️ 数据量较少（{len(df)} 条），部分长周期指标可能不完整，建议扩大日期范围。"
        )

    # ---------- 2. 计算指标 ----------
    with st.spinner("正在计算技术指标…"):
        df = calc_ma(df, ma_periods)
        df = calc_macd(df, macd_fast, macd_slow, macd_signal)
        df = calc_rsi(df, rsi_period)
        df = calc_kdj(df, kdj_n)
        df = calc_boll(df, boll_period, boll_std)

    # ---------- 3. 生成信号 ----------
    with st.spinner("正在生成交易信号…"):
        if strategy == "均线交叉":
            df = gen_ma_cross_signal(df, ma_fast, ma_slow)
        elif strategy == "MACD金叉死叉":
            df = gen_macd_signal(df)
        elif strategy == "RSI超买超卖":
            df = gen_rsi_signal(df, rsi_oversold, rsi_overbought)
        elif strategy == "布林带突破":
            df = gen_boll_signal(df)
        else:
            df = gen_composite_signal(df, ma_fast, ma_slow, rsi_oversold, rsi_overbought)

    # ---------- 4. 回测 ----------
    with st.spinner("正在执行回测…"):
        df, trades_df, metrics = backtest(df, init_capital, commission_rate, stamp_tax, slippage)

    if metrics is None:
        st.error("❌ 回测执行失败。")
        return

    # ---------- 5. 展示结果 ----------
    stock_name = get_stock_name(symbol)
    st.subheader(f"📊 {stock_name} · 分析结果")
    st.caption(
        f"数据区间：{df['date'].iloc[0].strftime('%Y-%m-%d')} ~ "
        f"{df['date'].iloc[-1].strftime('%Y-%m-%d')} ｜ "
        f"共 {len(df)} 个交易日 ｜ 策略：{strategy}"
    )

    # --- 绩效指标卡片 ---
    st.markdown("### 📈 回测绩效")
    pct = lambda v: f"{v * 100:.2f}%"

    m1, m2, m3, m4 = st.columns(4)
    m5, m6, m7, m8 = st.columns(4)
    m1.metric("总收益率", pct(metrics["total_return"]), delta=f"期末 ¥{metrics['final_equity']:,.0f}")
    m2.metric("年化收益率", pct(metrics["annual_return"]))
    m3.metric("最大回撤", pct(metrics["max_drawdown"]), delta="风险指标", delta_color="inverse")
    m4.metric("夏普比率", f"{metrics['sharpe']:.2f}")
    m5.metric("胜率", pct(metrics["win_rate"]))
    m6.metric("盈亏比", f"{metrics['profit_loss_ratio']:.2f}")
    m7.metric("交易次数", metrics["total_trades"])
    m8.metric("初始资金", f"¥{init_capital:,.0f}")

    # --- K线 + 副图 ---
    st.markdown("### 📉 行情与技术指标")
    with st.spinner("正在绘制图表…"):
        fig_kline = plot_kline_with_indicators(df, ma_periods)
        st.plotly_chart(fig_kline, use_container_width=True)

    # --- 资金曲线 + 回撤 ---
    st.markdown("### 💰 资金曲线与回撤")
    fig_equity = plot_equity_drawdown(df, init_capital)
    st.plotly_chart(fig_equity, use_container_width=True)

    # --- 交易明细 ---
    st.markdown("### 📋 交易明细")
    if trades_df is not None and not trades_df.empty:
        st.dataframe(trades_df, use_container_width=True, hide_index=True)
        csv_data = trades_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ 下载交易明细 CSV",
            data=csv_data,
            file_name=f"trades_{symbol}_{strategy}.csv",
            mime="text/csv",
        )
    else:
        st.info("该策略在此区间未产生交易信号，可尝试调整参数或扩大日期范围。")

    # --- 数据预览（折叠） ---
    with st.expander("🔍 查看原始数据与指标（前 20 行）"):
        display_cols = ["date", "open", "close", "high", "low", "volume"] + \
                       [f"MA{p}" for p in ma_periods] + ["DIF", "DEA", "MACD", "RSI", "K", "D", "J", "signal"]
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[display_cols].head(20), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
