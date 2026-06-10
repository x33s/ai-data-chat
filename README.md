# 📊 AI 数据分析助手

一个基于 RAG + Function Calling 的智能数据分析平台，支持自然语言查询数据、自动生成可视化图表。

## ✨ 功能特点

- 💬 **自然语言对话**：像聊天一样查询数据，无需学习 SQL
- 📊 **自动生成图表**：支持柱状图、折线图，自动选择最合适的图表类型
- 🔧 **Agent 工具调用**：AI 自动调用查询、画图等工具
- 📁 **多文件管理**：批量上传、切换、删除 CSV/Excel
- 🔍 **智能列识别**：自动识别销售额、产品、日期等列
- 💨 **流式输出**：逐字显示，体验如 ChatGPT
- 📎 **引用来源**：回答可追溯，可重新打开图表

## 🛠️ 技术栈

### 后端
- **FastAPI**：高性能 Web 框架
- **Function Calling**：Agent 工具调用
- **阿里云百炼（通义千问）**：大语言模型
- **Pandas**：数据处理
- **DuckDB**：SQL 查询引擎

### 前端
- **Vue 3**：渐进式框架
- **Element Plus**：UI 组件库
- **ECharts**：图表可视化
- **Vite**：构建工具

## 📁 项目结构
ai-data-chat/
├── backend/
│ ├── app.py # FastAPI 主程序
│ ├── agent.py # AI Agent 核心逻辑
│ ├── tools.py # Function Calling 工具定义
│ ├── data/ # 数据模块
│ │ ├── init.py
│ │ ├── manager.py # 文件管理
│ │ └── queries.py # 查询缓存
│ ├── nl_to_sql.py # 自然语言转 SQL
│ ├── requirements.txt # Python 依赖
│ └── .env # 环境变量
├── frontend/
│ ├── src/
│ │ ├── App.vue # 主界面
│ │ ├── components/ # 组件
│ │ └── api/ # API 接口
│ ├── package.json
│ └── index.html
└── README.md

text

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Node.js 16+
- 阿里云百炼 API Key（[免费领取](https://bailian.console.aliyun.com/)）

### 1. 克隆项目

```bash
git clone https://github.com/yourname/ai-data-chat.git
cd ai-data-chat
2. 配置后端
bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
# 创建 .env 文件，写入：
# DASHSCOPE_API_KEY=sk-your-api-key

# 启动后端
python app.py
后端服务运行在 http://localhost:8001

3. 配置前端
bash
# 新终端，进入前端目录
cd frontend

# 安装依赖
npm install

# 启动前端
npm run dev
前端界面运行在 http://localhost:5173

4. 使用
打开浏览器访问 http://localhost:5173

在聊天框输入问题，如：

"数据概览"

"哪个产品卖得最好？"

"画个柱状图"

"销售员业绩"

"月度趋势折线图"

🎯 核心原理
Agent + Function Calling 工作流程
text
用户: "哪个产品卖得最好？"
    ↓
LLM 理解意图 → 决定调用 query_sales_data 工具
    ↓
执行工具查询数据 → 返回结果
    ↓
LLM 整合结果 → "智能手机销售额最高，达到 ¥87,000"
图表生成流程
text
用户: "画个折线图"
    ↓
前端判断需要图表 → 调用 /chart 接口
    ↓
后端生成图表数据 (xAxis + series)
    ↓
前端 ECharts 渲染 → 弹窗显示 + 导出 PNG
📊 数据说明
项目支持任意 CSV/Excel 文件，自动识别列结构：

字段	说明
日期	销售日期
产品	产品名称
品类	产品分类
销售额	销售金额
销售员	销售人员
数量	销售数量
🧪 测试用例
输入	预期输出
"数据概览"	总记录数、总销售额、时间范围
"哪个产品卖得最好？"	返回销售额最高的产品
"画个柱状图"	各产品销售额柱状图
"销售员业绩"	销售员业绩排行
"月度趋势折线图"	月度销售额趋势折线图
📄 License
MIT

👨‍💻 作者
[x33s] - [https://github.com/x33s]

🙏 致谢
阿里云百炼 - 大模型 API

Vue 3 - 前端框架

Element Plus - UI 组件库

ECharts - 图表库