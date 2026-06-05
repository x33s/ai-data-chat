"""FastAPI 服务 - AI 数据分析助手"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from agent import DataAgent
from data_loader import get_data_info, load_data

# 创建 FastAPI 应用
app = FastAPI(title="AI 数据分析助手", version="1.0")

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 Agent 实例
agent = DataAgent()


# ============================================
# 请求/响应模型
# ============================================
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    data_info: Optional[Dict] = None


class ChartRequest(BaseModel):
    message: str


class ChartResponse(BaseModel):
    chart_type: str
    title: str
    xAxis: List[str]
    series: List[Dict]


# ============================================
# API 端点
# ============================================

@app.get("/")
async def root():
    return {
        "service": "AI 数据分析助手",
        "status": "running",
        "version": "1.0"
    }


@app.get("/info")
async def info():
    """获取数据概览"""
    try:
        return get_data_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """对话接口"""
    if not request.message:
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    try:
        # 调用 Agent
        answer = agent.chat(request.message)
        
        # 获取数据概览（如果用户问的是概览相关）
        keywords = ["数据", "概览", "总览", "统计", "整体"]
        need_info = any(kw in request.message for kw in keywords)
        data_info = get_data_info() if need_info else None
        
        return ChatResponse(answer=answer, data_info=data_info)
        
    except Exception as e:
        print(f"错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chart")
async def generate_chart(request: ChatRequest):
    """生成图表数据"""
    if not request.message:
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    try:
        # 调用 Agent 获取结构化图表数据
        result = agent.generate_chart_data(request.message)
        
        # 检查是否有错误
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # 确保返回的数据结构完整
        if not result.get("xAxis") or len(result["xAxis"]) == 0:
            raise HTTPException(status_code=400, detail="没有可用的图表数据")
        
        return {
            "chart_type": result.get("chart_type", "bar"),
            "title": result.get("title", "数据图表"),
            "xAxis": result["xAxis"],
            "series": result.get("series", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"图表生成错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear")
async def clear_history():
    """清空对话历史"""
    agent.clear_history()
    return {"message": "对话历史已清空"}


@app.get("/data/raw")
async def get_raw_data(limit: int = 20):
    """获取原始数据"""
    try:
        df = load_data()
        return df.head(limit).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 启动入口
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)