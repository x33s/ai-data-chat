"""Function Calling 工具定义"""
from data_loader import query_sales_data, get_data_info
from typing import Dict, Any

# 工具定义（用于 LLM）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_sales_data",
            "description": "查询销售数据。可以按日期范围、产品、品类、销售员进行筛选，返回销售额统计、产品排行等汇总信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "开始日期，格式 YYYY-MM-DD"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期，格式 YYYY-MM-DD"
                    },
                    "product": {
                        "type": "string",
                        "description": "产品名称"
                    },
                    "category": {
                        "type": "string",
                        "description": "品类"
                    },
                    "salesperson": {
                        "type": "string",
                        "description": "销售员姓名"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_info",
            "description": "获取数据概览信息，包括总销售额、产品列表、日期范围等。",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """执行工具调用"""
    if tool_name == "query_sales_data":
        return query_sales_data(**arguments)
    elif tool_name == "get_data_info":
        return get_data_info()
    else:
        return {"error": f"未知工具: {tool_name}"}