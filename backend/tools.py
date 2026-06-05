"""Function Calling 工具定义"""
from data_loader import query_sales_data, get_chart_data, get_data_info
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
                        "description": "开始日期，格式 YYYY-MM-DD，例如 2024-01-01"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期，格式 YYYY-MM-DD，例如 2024-03-31"
                    },
                    "product": {
                        "type": "string",
                        "description": "产品名称，如：智能手机、笔记本电脑、沙发、餐桌"
                    },
                    "category": {
                        "type": "string",
                        "description": "品类，如：电子产品、家居用品"
                    },
                    "salesperson": {
                        "type": "string",
                        "description": "销售员姓名，如：张三、李四、王芳"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_info",
            "description": "获取数据概览信息，包括总销售额、产品列表、日期范围等。用于了解整体情况。",
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
            "description": "生成图表数据。当用户要求画图、绘制图表、可视化数据时调用此工具。支持柱状图(bar)、折线图(line)、饼图(pie)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "description": "图表类型：bar(柱状图), line(折线图), pie(饼图)",
                        "enum": ["bar", "line", "pie"]
                    },
                    "data_type": {
                        "type": "string",
                        "description": "数据类型：product(产品销售额), salesperson(销售员业绩), category(品类销售), monthly(月度趋势)",
                        "enum": ["product", "salesperson", "category", "monthly"]
                    }
                },
                "required": ["chart_type"]
            }
        }
    }
]


# 工具执行函数
def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """执行工具调用"""
    if tool_name == "query_sales_data":
        return query_sales_data(**arguments)
    elif tool_name == "get_data_info":
        return get_data_info()
    elif tool_name == "generate_chart":
        return generate_chart(**arguments)
    else:
        return {"error": f"未知工具: {tool_name}"}


def generate_chart(chart_type: str = "bar", data_type: str = "product") -> Dict[str, Any]:
    """
    生成图表数据
    
    Args:
        chart_type: 图表类型 (bar, line, pie)
        data_type: 数据类型 (product, salesperson, category, monthly)
    
    Returns:
        图表配置数据
    """
    # 查询销售数据
    sales_data = query_sales_data()
    
    # 根据数据类型选择数据
    data_key_map = {
        "product": "product_sales",
        "salesperson": "salesperson_sales",
        "category": "category_sales",
        "monthly": "monthly_sales"
    }
    
    title_map = {
        "product": "各产品销售额",
        "salesperson": "销售员业绩",
        "category": "品类销售",
        "monthly": "月度销售趋势"
    }
    
    data_key = data_key_map.get(data_type, "product_sales")
    title = title_map.get(data_type, "销售数据")
    
    if data_key not in sales_data:
        return {"error": f"无法获取 {data_type} 数据"}
    
    series_data = sales_data[data_key]
    
    # 对月度数据进行排序
    if data_type == "monthly":
        sorted_keys = sorted(series_data.keys())
        x_data = sorted_keys
        y_data = [series_data[k] for k in sorted_keys]
    else:
        x_data = list(series_data.keys())
        y_data = list(series_data.values())
    
    return {
        "chart_type": chart_type,
        "title": title,
        "xAxis": x_data,
        "series": [{
            "name": "销售额",
            "data": y_data
        }],
        "total_sales": sales_data.get("total_sales", 0),
        "total_records": sales_data.get("total_records", 0)
    }