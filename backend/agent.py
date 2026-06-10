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
        self.current_dataset = None  # 记录当前数据集
        self.max_history = 20
        self.system_prompt = """你是专业的数据分析助手。你有以下能力：
1. 查询销售数据（query_sales_data）
2. 查看数据概况（get_data_info）
3. 生成图表（generate_chart）- 支持bar/line/pie
4. 执行SQL查询（execute_sql）

工作原则：
- 根据用户需求选择合适的工具
- 工具调用后，基于返回的data字段回答用户问题
- 回答要简洁、数据准确
- 记住对话上下文，支持连续对话

示例连续对话：
用户：总销售额多少？
助手：总销售额是204,500元。
用户：那哪个产品卖得最好？
助手：根据刚才的数据，智能手机卖得最好，销售额87,000元。"""
    
    def _check_dataset_change(self):
        """检查数据集是否切换，如果切换则清空对话历史"""
        from data_loader import _current_dataset
        if self.current_dataset != _current_dataset:
            if self.current_dataset is not None:
                print(f"数据集已切换: {self.current_dataset} -> {_current_dataset}，清空对话历史")
                self.conversation_history = []
            self.current_dataset = _current_dataset
    
    def _trim_history(self):
        """限制历史记录长度"""
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def chat(self, user_message: str) -> str:
        """处理用户消息"""
        # 检查数据集是否变化
        self._check_dataset_change()
        
        # 添加用户消息
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # 构建消息
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history
        
        # 第一次调用 LLM
        try:
            response = client.chat.completions.create(
                model="qwen-plus",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1
            )
        except Exception as e:
            return f"调用模型失败: {str(e)}"
        
        assistant_message = response.choices[0].message
        
        # 处理工具调用
        if assistant_message.tool_calls:
            # 保存助手消息
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
            
            # 执行所有工具
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                print(f"[工具调用] {tool_name}")
                print(f"[参数] {json.dumps(arguments, ensure_ascii=False)}")
                
                # 执行工具
                result = execute_tool(tool_name, arguments)
                
                print(f"[结果] {json.dumps(result, ensure_ascii=False)[:200]}...")
                
                # 添加工具结果
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })
            
            # 第二次调用生成最终回答
            final_messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history
            
            try:
                final_response = client.chat.completions.create(
                    model="qwen-plus",
                    messages=final_messages,
                    temperature=0.1
                )
                
                final_answer = final_response.choices[0].message.content
                
                # 保存最终回答
                self.conversation_history.append({
                    "role": "assistant",
                    "content": final_answer
                })
                
                # 限制历史长度
                self._trim_history()
                
                return final_answer
            
            except Exception as e:
                return f"生成回答失败: {str(e)}"
        
        # 没有工具调用
        if assistant_message.content:
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content
            })
            self._trim_history()
            return assistant_message.content
        
        return "抱歉，我无法回答这个问题。"
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        print("对话历史已清空")
    
    def get_info(self) -> Dict:
        """获取 Agent 信息"""
        from data_loader import get_data_info
        return get_data_info()
    
    def generate_chart_data(self, user_message: str) -> Dict:
        """生成结构化的图表数据（供前端直接调用）"""
        from data_loader import query_sales_data
        
        user_message_lower = user_message.lower()
        
        # 判断图表类型
        if "折线" in user_message_lower or "趋势" in user_message_lower:
            chart_type = "line"
        elif "饼图" in user_message_lower:
            chart_type = "pie"
        else:
            chart_type = "bar"
        
        # 判断数据类型
        if "销售员" in user_message_lower or "业绩" in user_message_lower:
            data_type = "salesperson"
        elif "月份" in user_message_lower or "月度" in user_message_lower or "趋势" in user_message_lower:
            data_type = "monthly"
            chart_type = "line"
        else:
            data_type = "product"
        
        # 调用图表生成逻辑
        from tools import generate_chart_logic
        return generate_chart_logic(chart_type, data_type)