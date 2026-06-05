# 进入 backend 目录
cd F:\trae\ai-data-chat\backend

# 创建虚拟环境（可选）
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置 .env 文件（填入你的 API Key）
# 编辑 backend/.env，写入 DASHSCOPE_API_KEY=sk-xxx

# 运行服务
python app.py