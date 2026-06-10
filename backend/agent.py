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
    """数据分析 Agent - 支持多轮对话"""
    
    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.current_dataset = None
        self.system_prompt = """你是专业的数据分析助手。你有以下能力：
1. 查询销售数据（query_sales_data）
2. 查看数据概况（get_data_info）
3. 生成图表（generate_chart）- 支持bar/line/pie
4. 执行SQL查询（execute_sql）

重要：结合对话历史理解用户问题。用户说"它"、"那个"、"再"、"然后"时，指代之前讨论的内容。

回答要求：简洁、准确，基于工具返回的数据。"""
    
    def _check_dataset_change(self):
        """数据集切换时清空历史"""
        try:
            from data_loader import _current_dataset
            if self.current_dataset != _current_dataset:
                if self.current_dataset is not None:
                    print(f"[数据集切换] 清空对话历史")
                    self.conversation_history = []
                self.current_dataset = _current_dataset
        except:
            pass
    
    def chat(self, user_message: str) -> str:
        """处理用户消息"""
        self._check_dataset_change()
        
        # 添加用户消息
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # 构建消息（包含完整历史）
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history
        
        # 限制历史长度（保留最近20条）
        if len(messages) > 22:
            messages = [messages[0]] + messages[-20:]
        
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
            
            # 执行工具
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                print(f"[工具] {tool_name}: {arguments}")
                result = execute_tool(tool_name, arguments)
                
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })
            
            # 生成最终回答
            final_messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history
            
            final_response = client.chat.completions.create(
                model="qwen-plus",
                messages=final_messages,
                temperature=0.1
            )
            
            final_answer = final_response.choices[0].message.content
            self.conversation_history.append({
                "role": "assistant",
                "content": final_answer
            })
            
            return final_answer
        
        # 无工具调用
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
        print("对话历史已清空")
    
    def get_info(self) -> Dict:
        from data_loader import get_data_info
        return get_data_info()
    
    def generate_chart_data(self, user_message: str) -> Dict:
        from data_loader import query_sales_data
        
        msg = user_message.lower()
        
        if "折线" in msg or "趋势" in msg:
            chart_type = "line"
        elif "饼图" in msg:
            chart_type = "pie"
        else:
            chart_type = "bar"
        
        if "销售员" in msg or "业绩" in msg:
            data_type = "salesperson"
        elif "月份" in msg or "月度" in msg or "趋势" in msg:
            data_type = "monthly"
            chart_type = "line"
        else:
            data_type = "product"
        
        from tools import generate_chart_logic
        return generate_chart_logic(chart_type, data_type)

    def chat_stream(self, user_message: str):
        """流式处理用户消息 - 支持工具调用"""
        self._check_dataset_change()
        
        # 添加用户消息到历史
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # 构建消息
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history
        
        try:
            # 第一次调用：判断是否需要工具（不使用流式）
            response = client.chat.completions.create(
                model="qwen-plus",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1
            )
            
            assistant_message = response.choices[0].message
            
            # 如果需要工具调用
            if assistant_message.tool_calls:
                # 保存工具调用消息
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
                
                # 执行工具
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    print(f"[工具调用] {tool_name}: {arguments}")
                    
                    # 执行工具
                    result = execute_tool(tool_name, arguments)
                    
                    # 添加工具结果
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                
                # 第二次调用：生成最终回答（流式输出）
                final_messages = [
                    {"role": "system", "content": self.system_prompt}
                ] + self.conversation_history
                
                # 流式输出时不要传 tools 参数
                stream = client.chat.completions.create(
                    model="qwen-plus",
                    messages=final_messages,
                    temperature=0.1,
                    stream=True
                )
                
                full_content = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content += content
                        yield content
                
                # 保存最终回答
                self.conversation_history.append({
                    "role": "assistant",
                    "content": full_content
                })
            
            else:
                # 没有工具调用，直接流式输出
                # 流式输出时不要传 tools 参数
                stream = client.chat.completions.create(
                    model="qwen-plus",
                    messages=messages,
                    temperature=0.1,
                    stream=True
                )
                
                full_content = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content += content
                        yield content
                
                # 保存到历史
                self.conversation_history.append({
                    "role": "assistant",
                    "content": full_content
                })
            
        except Exception as e:
            print(f"流式错误: {e}")
            import traceback
            traceback.print_exc()
            yield f"调用失败: {str(e)}"