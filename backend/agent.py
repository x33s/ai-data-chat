"""Agent 核心逻辑 - 处理对话和工具调用"""
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any

from tools import TOOLS, execute_tool

load_dotenv()

# 初始化客户端
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


class DataAgent:
    """数据分析 Agent"""
    
    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.system_prompt = """你是一个专业的数据分析助手。你可以查询销售数据、生成图表、执行SQL查询并回答用户问题。

当前数据表信息：
- 表名: sales
- 列名: 日期(date), 产品(product), 品类(category), 销售额(sales_amount), 销售员(salesperson), 数量(quantity)

工作流程：
1. 理解用户的问题
2. 如果需要查询数据，调用 query_sales_data 工具
3. 如果需要了解数据概况，调用 get_data_info 工具
4. 如果用户要求画图、绘制图表、可视化数据，调用 generate_chart 工具
5. 如果用户明确要求使用SQL查询、想看SQL语句或进行复杂数据分析，调用 execute_sql 工具
6. 基于查询结果回答用户的问题

工具使用说明：
- query_sales_data: 查询销售数据，可以按日期范围、产品、品类、销售员筛选
- get_data_info: 获取数据概览，了解整体情况
- generate_chart: 用于生成图表数据。支持 bar(柱状图), line(折线图), pie(饼图)
- execute_sql: 执行SQL查询。当用户说"用SQL查询"、"写个SQL"、"执行SQL"等时使用。只支持SELECT查询。
  - sql: SQL语句，表名固定为 sales，例如：SELECT * FROM sales WHERE 品类='电子产品'

回答要求：
- 用简洁清晰的语言总结数据
- 如果用户问趋势、排行等，主动指出关键发现
- 如果用户要求画图，调用 generate_chart 工具后，用自然语言描述图表内容
- 如果用户要求SQL查询，调用 execute_sql 工具后，展示执行的SQL和查询结果

示例：
用户问："哪个产品卖得最好？"
你应该：先调用 query_sales_data 获取数据，然后回答。

用户说："画个柱状图"
你应该：调用 generate_chart(chart_type="bar", data_type="product")

用户说："写个SQL查询电子产品的销售数据"
你应该：调用 execute_sql(sql="SELECT * FROM sales WHERE 品类='电子产品'")"""
    
    def chat(self, user_message: str) -> str:
        """处理用户消息"""
        # 添加用户消息到历史
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history
        
        # 第一次调用 LLM
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.1
        )
        
        assistant_message = response.choices[0].message
        
        # 检查是否需要调用工具
        if assistant_message.tool_calls:
            # 添加助手消息（包含工具调用）
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            # 执行每个工具调用
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                print(f"[TOOL] 调用工具: {tool_name}")
                print(f"   参数: {arguments}")
                
                # 执行工具
                result = execute_tool(tool_name, arguments)
                
                # 添加工具结果到历史
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })
            
            # 第二次调用 LLM，整合工具结果
            final_messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history
            
            final_response = client.chat.completions.create(
                model="qwen-plus",
                messages=final_messages,
                temperature=0.1
            )
            
            final_answer = final_response.choices[0].message.content
            
            # 添加最终回答到历史
            self.conversation_history.append({
                "role": "assistant",
                "content": final_answer
            })
            
            return final_answer
        
        # 没有工具调用，直接返回
        if assistant_message.content:
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content
            })
            return assistant_message.content
        
        return "抱歉，我无法回答这个问题。"
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
    
    def get_info(self) -> Dict:
        """获取 Agent 信息"""
        from data_loader import get_data_info
        return get_data_info()
    
    def generate_chart_data(self, user_message: str) -> Dict:
        """生成结构化的图表数据"""
        from data_loader import query_sales_data, get_current_data_info
        
        # 获取当前数据信息
        data_info = get_current_data_info()
        print(f"当前数据: {data_info}")
        
        # 查询销售数据
        result = query_sales_data()
        print(f"查询结果: {result}")
        
        # 判断图表类型
        chart_type = "bar"
        if "折线" in user_message or "趋势" in user_message:
            chart_type = "line"
        elif "饼图" in user_message:
            chart_type = "pie"
        
        # 判断数据类型
        if "销售员" in user_message or "业绩" in user_message:
            if result.get("salesperson_sales"):
                x_data = list(result["salesperson_sales"].keys())
                y_data = list(result["salesperson_sales"].values())
                title = "销售员业绩对比"
            else:
                return {"error": "没有销售员数据"}
        elif "月份" in user_message or "月度" in user_message or "趋势" in user_message:
            if result.get("monthly_sales"):
                # 按月份排序
                months = sorted(result["monthly_sales"].keys())
                x_data = months
                y_data = [result["monthly_sales"][m] for m in months]
                title = "月度销售额趋势"
                chart_type = "line"  # 强制折线图
            else:
                return {"error": "没有月度数据"}
        else:
            # 默认产品数据
            if result.get("product_sales"):
                x_data = list(result["product_sales"].keys())
                y_data = list(result["product_sales"].values())
                title = "各产品销售额对比"
            else:
                return {"error": "没有产品数据"}
        
        return {
            "chart_type": chart_type,
            "title": title,
            "xAxis": x_data,
            "series": [{
                "name": "销售额",
                "data": y_data
            }]
        }