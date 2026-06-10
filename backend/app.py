"""FastAPI 服务 - AI 数据分析助手"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from agent import DataAgent
from data_loader import (
    get_data_info, 
    load_data, 
    parse_uploaded_file, 
    update_data_from_upload,
    get_all_datasets,
    get_current_data_info,
    save_uploaded_files,
    switch_dataset,
    delete_dataset,
    get_data_preview
)
from nl_to_sql import get_nl_to_sql

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


class NLQueryRequest(BaseModel):
    question: str


class NLQueryResponse(BaseModel):
    success: bool
    answer: str
    query_info: Optional[Dict] = None
    data: Optional[List] = None
    row_count: Optional[int] = None


# ============================================
# 基础 API 端点
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


# ============================================
# 数据集管理接口（核心 - 支持多文件上传）
# ============================================

@app.get("/datasets")
async def list_datasets():
    """获取所有数据集"""
    try:
        datasets = get_all_datasets()
        return {"datasets": datasets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/datasets/current")
async def get_current_dataset():
    """获取当前激活的数据集"""
    try:
        result = get_current_data_info()
        return result if result else {"message": "没有激活的数据集"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/datasets/upload")
async def upload_datasets(files: List[UploadFile] = File(...)):
    """批量上传数据集（支持多文件）"""
    try:
        results = save_uploaded_files(files)
        
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "success": success_count > 0,
            "total": len(results),
            "success_count": success_count,
            "fail_count": len(results) - success_count,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_single_file(file: UploadFile = File(...)):
    """单文件上传（兼容旧接口）"""
    try:
        file_content = await file.read()
        result = update_data_from_upload(file_content, file.filename)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "上传失败"))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/datasets/switch")
async def switch_dataset_api(filename: str = Form(...)):
    """切换数据集"""
    try:
        result = switch_dataset(filename)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "切换失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/datasets/{filename}")
async def delete_dataset_api(filename: str):
    """删除数据集"""
    try:
        result = delete_dataset(filename)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "删除失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/datasets/preview")
async def preview_dataset(limit: int = 10):
    """获取数据预览"""
    try:
        return get_data_preview(limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/upload/parse")
async def parse_file_only(file: UploadFile = File(...)):
    """仅解析文件，不更新全局数据缓存（用于预览）"""
    try:
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="文件为空")
        
        parse_result = parse_uploaded_file(file_content, file.filename)
        
        if not parse_result.get("success"):
            raise HTTPException(status_code=400, detail=parse_result.get("error", "文件解析失败"))
        
        return {
            "success": True,
            "message": "文件解析成功",
            "data": parse_result["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"文件解析错误: {e}")
        raise HTTPException(status_code=500, detail=f"解析文件时发生错误: {str(e)}")


# ============================================
# 对话和查询接口
# ============================================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """对话接口"""
    if not request.message:
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    try:
        answer = agent.chat(request.message)
        
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
        result = agent.generate_chart_data(request.message)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
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
# 自然语言转 SQL 接口（亮点功能）
# ============================================

@app.post("/nl/query", response_model=NLQueryResponse)
async def natural_language_query(request: NLQueryRequest):
    """自然语言查询接口 - 演示 NL 转 SQL"""
    if not request.question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    try:
        engine = get_nl_to_sql()
        if engine is None:
            return NLQueryResponse(
                success=False,
                answer="请先上传数据文件"
            )
        
        result = engine.ask(request.question)
        
        return NLQueryResponse(
            success=result["success"],
            answer=result.get("answer", ""),
            query_info=result.get("query_info"),
            data=result.get("data"),
            row_count=result.get("row_count")
        )
        
    except Exception as e:
        print(f"NL 查询错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nl/schema")
async def get_schema():
    """获取数据表结构"""
    try:
        engine = get_nl_to_sql()
        if engine is None:
            return {"error": "请先上传数据文件"}
        
        return {
            "columns": engine.columns,
            "column_types": engine.column_types,
            "sample_data": engine.sample_data,
            "row_count": len(engine.df)
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================
# 启动入口
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)