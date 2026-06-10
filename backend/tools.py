"""工具定义和执行逻辑"""
import json
from typing import Dict, Any
from data_loader import query_sales_data, get_data_info, execute_sql_query

# 工具定义（给模型看的）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_sales_data",
            "description": "查询销售数据，支持按日期范围、产品、品类、销售员筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "开始日期，格式YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "结束日期，格式YYYY-MM-DD"},
                    "product": {"type": "string", "description": "产品名称"},
                    "category": {"type": "string", "description": "品类名称"},
                    "salesperson": {"type": "string", "description": "销售员姓名"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_info",
            "description": "获取数据概览信息，包括总销售额、记录数、时间范围等",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_chart",
            "description": "生成图表数据，支持柱状图、折线图、饼图",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie"],
                        "description": "图表类型：bar柱状图，line折线图，pie饼图"
                    },
                    "data_type": {
                        "type": "string",
                        "enum": ["product", "salesperson", "monthly"],
                        "description": "数据类型：product按产品，salesperson按销售员，monthly按月"
                    }
                },
                "required": ["chart_type", "data_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": "执行SQL查询，只支持SELECT语句，表名为sales",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL查询语句，例如：SELECT * FROM sales WHERE 品类='电子产品'"}
                },
                "required": ["sql"]
            }
        }
    }
]


def generate_chart_logic(chart_type: str, data_type: str) -> Dict[str, Any]:
    """生成图表数据的核心逻辑"""
    from data_loader import query_sales_data
    
    # 获取数据
    result = query_sales_data()
    
    # 根据数据类型提取数据
    if data_type == "product":
        if not result.get("product_sales"):
            return {"error": "没有产品数据"}
        x_data = list(result["product_sales"].keys())
        y_data = list(result["product_sales"].values())
        title = "各产品销售额对比"
    
    elif data_type == "salesperson":
        if not result.get("salesperson_sales"):
            return {"error": "没有销售员数据"}
        x_data = list(result["salesperson_sales"].keys())
        y_data = list(result["salesperson_sales"].values())
        title = "销售员业绩对比"
    
    elif data_type == "monthly":
        if not result.get("monthly_sales"):
            return {"error": "没有月度数据"}
        months = sorted(result["monthly_sales"].keys())
        x_data = months
        y_data = [result["monthly_sales"][m] for m in months]
        title = "月度销售额趋势"
        # 月度数据强制使用折线图
        chart_type = "line"
    
    else:
        return {"error": f"不支持的数据类型: {data_type}"}
    
    return {
        "chart_type": chart_type,
        "title": title,
        "xAxis": x_data,
        "series": [{"name": "销售额", "data": y_data}]
    }


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """执行工具调用"""
    try:
        if tool_name == "query_sales_data":
            result = query_sales_data(**arguments)
            return {"success": True, "data": result}
        
        elif tool_name == "get_data_info":
            result = get_data_info()
            return {"success": True, "data": result}
        
        elif tool_name == "generate_chart":
            # 调用图表生成逻辑
            result = generate_chart_logic(
                arguments.get("chart_type", "bar"), 
                arguments.get("data_type", "product")
            )
            return {"success": True, "data": result}
        
        elif tool_name == "execute_sql":
            result = execute_sql_query(arguments.get("sql", ""))
            return {"success": True, "data": result}
        
        else:
            return {"success": False, "error": f"未知工具: {tool_name}"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}