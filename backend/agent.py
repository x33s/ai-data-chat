"""Agent 核心逻辑 - 处理对话和工具调用（支持大模型路由）"""
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any, Generator

from tools import TOOLS, execute_tool
from llm_router import get_router

load_dotenv()

# 初始化客户端（保留作为降级方案）
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


class DataAgent:
    """数据分析 Agent - 支持多轮对话 + 大模型路由"""
    
    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.current_dataset = None
        self.router = get_router()  # 初始化路由器
        
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
            from data import _current_dataset
            if self.current_dataset != _current_dataset:
                if self.current_dataset is not None:
                    print(f"[数据集切换] 清空对话历史")
                    self.conversation_history = []
                self.current_dataset = _current_dataset
        except:
            pass
    
    def _build_messages(self, include_history=True):
        """构建消息列表"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if include_history:
            messages += self.conversation_history
        
        # 限制历史长度（保留最近20条）
        if len(messages) > 22:
            messages = [messages[0]] + messages[-20:]
        
        return messages
    
    def _execute_tool_calls(self, tool_calls):
        """执行工具调用"""
        for tc in tool_calls:
            tool_name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"[工具] {tool_name}: {args}")
            
            result = execute_tool(tool_name, args)
            
            self.conversation_history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False)
            })
    
    def _call_with_fallback(self, messages, **kwargs):
        """带降级的模型调用"""
        try:
            # 优先使用路由器
            if self.router and self.router.has_clients():
                return self.router.chat(messages, **kwargs)
            else:
                # 降级到默认客户端
                return client.chat.completions.create(
                    model="qwen-plus",
                    messages=messages,
                    **kwargs
                )
        except Exception as e:
            print(f"[路由调用失败] {e}, 降级到默认模型")
            return client.chat.completions.create(
                model="qwen-plus",
                messages=messages,
                **kwargs
            )
    
    def _call_stream_with_fallback(self, messages, **kwargs):
        """带降级的流式模型调用"""
        try:
            if self.router and self.router.has_clients():
                return self.router.chat_stream(messages, **kwargs)
            else:
                return client.chat.completions.create(
                    model="qwen-plus",
                    messages=messages,
                    stream=True,
                    **kwargs
                )
        except Exception as e:
            print(f"[路由流式调用失败] {e}, 降级到默认模型")
            return client.chat.completions.create(
                model="qwen-plus",
                messages=messages,
                stream=True,
                **kwargs
            )
    
    def chat(self, user_message: str) -> str:
        """处理用户消息（支持智能路由）"""
        self._check_dataset_change()
        
        # 添加用户消息
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        messages = self._build_messages()
        
        try:
            # 使用路由器调用（自动选择模型）
            response = self._call_with_fallback(
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1
            )
        except Exception as e:
            return f"调用模型失败: {str(e)}"
        
        # 兼容不同返回格式
        if hasattr(response, 'choices'):
            assistant_message = response.choices[0].message
        else:
            return f"响应格式错误: {response}"
        
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
            self._execute_tool_calls(assistant_message.tool_calls)
            
            # 生成最终回答
            final_messages = self._build_messages()
            final_response = self._call_with_fallback(
                messages=final_messages,
                temperature=0.1
            )
            
            if hasattr(final_response, 'choices'):
                final_answer = final_response.choices[0].message.content
            else:
                final_answer = str(final_response)
            
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
    
    def chat_stream(self, user_message: str) -> Generator[str, None, None]:
        """流式处理用户消息（支持智能路由）"""
        self._check_dataset_change()
        
        # 添加用户消息
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        messages = self._build_messages()
        
        try:
            # 第一次调用：判断是否需要工具
            response = self._call_with_fallback(
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1
            )
            
            if hasattr(response, 'choices'):
                assistant_message = response.choices[0].message
            else:
                yield f"响应格式错误: {response}"
                return
            
            # 如果需要工具调用
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
                self._execute_tool_calls(assistant_message.tool_calls)
                
                # 流式生成最终回答
                final_messages = self._build_messages()
                stream = self._call_stream_with_fallback(
                    messages=final_messages,
                    temperature=0.1
                )
                
                full_content = ""
                for chunk in stream:
                    if isinstance(chunk, str):
                        full_content += chunk
                        yield chunk
                    elif hasattr(chunk, 'choices') and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content += content
                        yield content
                
                self.conversation_history.append({
                    "role": "assistant",
                    "content": full_content
                })
            
            else:
                # 直接流式输出
                stream = self._call_stream_with_fallback(
                    messages=messages,
                    temperature=0.1
                )
                
                full_content = ""
                for chunk in stream:
                    if isinstance(chunk, str):
                        full_content += chunk
                        yield chunk
                    elif hasattr(chunk, 'choices') and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content += content
                        yield content
                
                self.conversation_history.append({
                    "role": "assistant",
                    "content": full_content
                })
            
        except Exception as e:
            print(f"流式错误: {e}")
            import traceback
            traceback.print_exc()
            yield f"调用失败: {str(e)}"
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        print("对话历史已清空")
    
    def get_info(self) -> Dict:
        from data import get_data_info
        return get_data_info()
    
    def generate_chart_data(self, user_message: str) -> Dict:
        from data import query_sales_data
        
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