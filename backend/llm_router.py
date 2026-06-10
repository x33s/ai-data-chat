"""大模型路由器 - 简化版（只使用通义千问）"""
import os
from openai import OpenAI
from typing import List, Dict, Any, Generator
from dotenv import load_dotenv

load_dotenv()

# 初始化通义千问客户端
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


class LLMRouter:
    """简化的路由器 - 固定使用通义千问"""
    
    def __init__(self):
        self.model_name = "qwen-plus"
        self.stats = {"total_requests": 0, "model": "qwen-plus"}
        print(f"[路由器] 使用模型: {self.model_name}")
    
    def has_clients(self) -> bool:
        return True
    
    def get_stats(self) -> Dict:
        return self.stats
    
    def chat(self, messages: List[Dict], **kwargs) -> Any:
        """调用通义千问"""
        self.stats["total_requests"] += 1
        return client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            **kwargs
        )
    
    def chat_stream(self, messages: List[Dict], **kwargs) -> Generator:
        """流式调用通义千问"""
        self.stats["total_requests"] += 1
        stream = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True,
            **kwargs
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# 全局实例
_router = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router