# A股量化策略分析器

基于 **Streamlit + AkShare + Plotly** 的交互式 A 股量化分析与回测 Web 应用。

## 功能特性

* **行情数据**：AkShare 获取 A 股前复权日线数据
* **技术指标**：MA / MACD / RSI / KDJ / 布林带
* **交易策略**：均线交叉、MACD 金叉死叉、RSI 超买超卖、布林带突破、综合投票
* **回测引擎**：T+1 次日开盘成交、全仓买卖、佣金 + 印花税 + 滑点
* **可视化**：K 线 + 副图联动、资金曲线、回撤曲线、买卖信号标记
* **绩效指标**：总收益率、年化收益率、最大回撤、夏普比率、胜率、盈亏比
* **交易明细**：可下载 CSV

## 文件清单

```
stock\_quant\_analyzer/
├── app.py              # Streamlit 主程序（全部逻辑）
├── requirements.txt    # Python 依赖
└── README.md           # 本说明文档
```

\---

## 一、本地运行

### 1\. 环境要求

* Python 3.9 或更高版本
* 可访问互联网（AkShare 需从东方财富等数据源拉取行情）

### 2\. 安装依赖

```bash
# 进入项目目录
cd stock\_quant\_analyzer

# （推荐）创建虚拟环境
python -m venv venv
# Windows: venv\\Scripts\\activate
# macOS/Linux: source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3\. 启动应用

```bash
streamlit run app.py
```

启动后浏览器会自动打开 `http://localhost:8501`。若未自动打开，手动访问该地址即可。

### 4\. 使用方法

1. 在左侧侧边栏输入股票代码（如 `600141`）、日期范围
2. 设置初始资金、佣金费率、印花税率、滑点
3. 调整技术指标参数（均线周期、MACD、RSI、布林带等）
4. 选择交易策略
5. 点击「运行分析」
6. 查看绩效卡片、K 线图、资金曲线、交易明细，可下载 CSV

\---

## 二、部署到 Streamlit Cloud

Streamlit Cloud（share.streamlit.io）是 Streamlit 官方提供的免费托管平台，最适合部署本应用。

### 步骤 1：准备 GitHub 仓库

1. 在 GitHub 上创建一个新仓库（Public 或 Private 均可）
2. 将以下文件推送到仓库根目录：

```
   your-repo/
   ├── app.py
   ├── requirements.txt
   └── README.md（可选）
   ```

   推送命令示例：

```bash
   git init
   git add app.py requirements.txt README.md
   git commit -m "init: A股量化策略分析器"
   git branch -M main
   git remote add origin https://github.com/你的用户名/你的仓库名.git
   git push -u origin main
   ```

### 步骤 2：注册并登录 Streamlit Cloud

1. 访问 [https://share.streamlit.io](https://share.streamlit.io)
2. 点击 **"Sign in with GitHub"**，用 GitHub 账号登录
3. 首次登录需授权 Streamlit 访问你的 GitHub 仓库

### 步骤 3：创建应用

1. 登录后点击 **"New app"** 按钮
2. 填写部署信息：

|字段|填写内容|
|-|-|
|Repository|选择你的 GitHub 仓库|
|Branch|`main`（或 `master`）|
|Main file path|`app.py`|

3. 点击 **"Advanced settings"**（可选）：

   * Python version：选择 `3.11` 或 `3.10`
   * Secrets：本应用不需要额外环境变量，留空即可
4. 点击 **"Deploy!"** 开始部署

### 步骤 4：等待部署完成

* Streamlit Cloud 会自动读取 `requirements.txt` 并安装依赖
* 首次部署约需 3–5 分钟（AkShare 依赖较多）
* 部署成功后会自动跳转到应用页面，URL 格式为：
`https://<你的用户名>-<仓库名>-<随机字符串>.streamlit.app`

### 步骤 5：后续更新

* 每次 `git push` 到仓库后，Streamlit Cloud 会自动检测并重新部署
* 也可在应用管理页面手动点击 **"Reboot"** 重启

### 注意事项

* **AkShare 数据源**：Streamlit Cloud 服务器位于海外，访问国内数据源（东方财富等）可能较慢或偶发超时。若频繁超时，可考虑使用国内云服务器部署。
* **休眠机制**：免费版应用若连续几天无访问会进入休眠，首次打开需等待冷启动（约 30 秒）。
* **资源限制**：免费版提供约 1GB 内存，本应用轻量，足够使用。

\---

## 三、部署到 Hugging Face Spaces

Hugging Face Spaces 支持 Streamlit 运行时，也是免费托管的优质选择。

### 方式 A：通过网页界面创建（推荐新手）

1. 访问 [https://huggingface.co/spaces](https://huggingface.co/spaces)，点击 **"Create new Space"**
2. 填写信息：

|字段|填写内容|
|-|-|
|Space name|自定义，如 `stock-quant-analyzer`|
|License|任选（如 MIT）|
|Space SDK|选择 **Streamlit**|
|App file|`app.py`|
|Hardware|免费的 `CPU basic` 即可|

3. 点击 **"Create Space"**
4. 创建后进入 Space 页面，点击 **"Files"** 标签页
5. 点击 **"Add file" → "Upload files"**，上传 `app.py` 和 `requirements.txt`
6. 上传完成后，Hugging Face 会自动构建并启动应用
7. 点击 **"App"** 标签页即可访问

### 方式 B：通过 Git 推送（推荐开发者）

1. 先在网页上创建 Space（同上步骤 1–3）
2. 本地克隆 Space 仓库：

```bash
   git clone https://huggingface.co/spaces/你的用户名/stock-quant-analyzer
   cd stock-quant-analyzer
   ```

3. 将 `app.py` 和 `requirements.txt` 复制进去
4. 提交并推送：

```bash
   git add app.py requirements.txt
   git commit -m "init: A股量化策略分析器"
   git push
   ```

5. 推送后 Hugging Face 自动构建，构建日志可在 Space 页面的 **"Logs"** 中查看

### 重要：packages.txt（系统依赖）

Hugging Face Spaces 的 Streamlit 运行时通常已包含基础系统库。若 AkShare 运行时报缺系统库错误，可在仓库根目录添加 `packages.txt`：

```
libgl1-mesa-glx
libglib2.0-0
```

### 注意事项

* **访问 URL**：`https://huggingface.co/spaces/你的用户名/stock-quant-analyzer`
* **休眠机制**：免费 Space 48 小时无访问会休眠，打开时需等待重启
* **网络问题**：Hugging Face 服务器在海外，AkShare 拉取国内数据可能较慢，属正常现象
* **隐私**：Space 默认公开，若不想让他人访问，可在设置中将 Space 设为私有（需付费账户）

\---

## 四、其他部署方式（备选）

### 国内云服务器（推荐用于生产使用）

若 Streamlit Cloud / Hugging Face 因网络问题访问 AkShare 不稳定，可使用国内云服务器：

```bash
# 1. 安装 Python 3.9+ 和 pip
# 2. 上传项目文件
# 3. 安装依赖
pip install -r requirements.txt

# 4. 后台运行（使用 nohup 或 systemd）
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>\&1 \&

# 5. 在云服务器安全组中放行 8501 端口
# 6. 浏览器访问 http://服务器IP:8501
```

建议配合 Nginx 反向代理 + HTTPS 使用。

\---

## 五、常见问题

### Q1：提示"数据获取失败"或返回空数据？

* 检查股票代码是否为 6 位纯数字
* 确认日期范围内有交易日（避开刚上市的股票）
* 网络是否能访问东方财富等数据源（海外服务器可能受限）

### Q2：AkShare 接口报错？

* 升级到最新版：`pip install --upgrade akshare`
* AkShare 接口可能随数据源变化而调整，关注 [AkShare 官方文档](https://akshare.akfamily.xyz/)

### Q3：图表不显示或显示空白？

* 确认 Plotly 版本 >= 5.17
* 清除浏览器缓存后刷新
* Streamlit Cloud 上首次加载图表可能较慢

### Q4：回测结果与实盘差异大？

* 本回测为简化模型：T+1、全仓、无涨跌停限制、无停牌处理
* 滑点和佣金为固定比例，实盘可能更复杂
* 仅供策略研究参考，不构成投资建议

\---

## 免责声明

本工具仅用于量化交易学习与研究，所有回测结果基于历史数据，不代表未来收益。股市有风险，投资需谨慎。

