"""大模型路由器 - 智能选择最优模型"""
import os
from openai import OpenAI
from typing import Dict, Any, List, Generator
from enum import Enum

# ========== 模型配置 ==========
class ModelProvider(Enum):
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    # 可扩展更多模型


MODEL_CONFIGS = {
    ModelProvider.DEEPSEEK: {
        "name": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "cost_per_1k": 0,  # 免费
        "max_tokens": 1024 * 1024,  # 1M 上下文
        "strength": ["speed", "cost", "long_context", "code"],
    },
    ModelProvider.QWEN: {
        "name": "qwen-plus",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "cost_per_1k": 0.02,  # 约 0.02 元/1K
        "max_tokens": 128 * 1024,
        "strength": ["stability", "chinese", "data_analysis"],
    }
}


class LLMRouter:
    """大模型路由器 - 智能选择模型"""
    
    def __init__(self):
        # 先初始化统计（必须在 _init_clients 之前）
        self.stats = {
            "total_requests": 0,
            "model_usage": {},
            "fallback_count": 0
        }
        self.clients = {}
        # 再初始化客户端
        self._init_clients()
    
    def _init_clients(self):
        """初始化所有模型客户端"""
        for provider, config in MODEL_CONFIGS.items():
            api_key = os.getenv(config["api_key_env"])
            if api_key and api_key != "sk-your-deepseek-key" and api_key != "sk-your-dashscope-key":
                try:
                    self.clients[provider] = OpenAI(
                        api_key=api_key,
                        base_url=config["base_url"],
                    )
                    self.stats["model_usage"][provider.value] = 0
                    print(f"[路由器] ✅ 已加载模型: {provider.value} ({config['name']})")
                except Exception as e:
                    print(f"[路由器] ❌ 加载模型失败 {provider.value}: {e}")
            else:
                print(f"[路由器] ⚠️ 跳过模型 {provider.value}: 未配置 API Key")
        
        if not self.clients:
            print("[路由器] ⚠️ 警告: 没有可用的模型客户端")
    
    def _analyze_question(self, question: str) -> Dict:
        """分析问题特征"""
        q_lower = question.lower()
        
        # 问题长度
        length = len(question)
        
        # 关键词检测
        keywords = {
            "code": ["代码", "写个", "实现", "函数", "class", "def", "编程", "程序"],
            "data": ["数据", "查询", "销售", "统计", "分析", "图表", "汇总"],
            "chat": ["你好", "谢谢", "怎么样", "觉得", "帮助"],
            "translate": ["翻译", "译成", "english", "英文"],
            "long": ["长篇", "文章", "总结", "报告", "详细"],
            "sql": ["sql", "查询语句", "数据库", "select", "from", "where"],
        }
        
        types = []
        for type_name, words in keywords.items():
            if any(w in q_lower for w in words):
                types.append(type_name)
        
        # 判断复杂度
        complexity = "simple"
        if length > 200 or len(types) > 2:
            complexity = "complex"
        elif length > 50 or "代码" in q_lower or "分析" in q_lower:
            complexity = "medium"
        
        return {
            "length": length,
            "types": types,
            "complexity": complexity,
        }
    
    def select_model(self, question: str) -> ModelProvider:
        """根据问题选择最优模型"""
        analysis = self._analyze_question(question)
        
        print(f"[路由分析] 长度={analysis['length']}, 类型={analysis['types']}, 复杂度={analysis['complexity']}")
        
        # 检查可用模型
        available_models = list(self.clients.keys())
        if not available_models:
            print("[路由警告] 没有可用的模型，使用默认配置")
            return ModelProvider.QWEN
        
        # 规则1：超长上下文 → DeepSeek（1M 上下文）
        if analysis["length"] > 5000:
            if ModelProvider.DEEPSEEK in available_models:
                print("[路由决策] 超长问题 (>5000字) → DeepSeek")
                return ModelProvider.DEEPSEEK
        
        # 规则2：代码/SQL 生成 → DeepSeek（免费，代码能力强）
        if "code" in analysis["types"] or "sql" in analysis["types"]:
            if ModelProvider.DEEPSEEK in available_models:
                print("[路由决策] 代码/SQL问题 → DeepSeek")
                return ModelProvider.DEEPSEEK
        
        # 规则3：数据分析 → 通义千问（稳定，中文理解好）
        if "data" in analysis["types"]:
            if ModelProvider.QWEN in available_models:
                print("[路由决策] 数据分析问题 → 通义千问")
                return ModelProvider.QWEN
        
        # 规则4：简单闲聊/翻译 → DeepSeek（免费）
        if analysis["complexity"] == "simple" and ("chat" in analysis["types"] or "translate" in analysis["types"]):
            if ModelProvider.DEEPSEEK in available_models:
                print("[路由决策] 简单闲聊/翻译 → DeepSeek")
                return ModelProvider.DEEPSEEK
        
        # 规则5：复杂任务 → 通义千问（更稳定）
        if analysis["complexity"] == "complex":
            if ModelProvider.QWEN in available_models:
                print("[路由决策] 复杂任务 → 通义千问")
                return ModelProvider.QWEN
        
        # 默认：优先使用 DeepSeek（免费），否则使用第一个可用模型
        default = ModelProvider.DEEPSEEK if ModelProvider.DEEPSEEK in available_models else available_models[0]
        print(f"[路由决策] 默认 → {default.value}")
        return default
    
    def _get_client_and_config(self, question: str):
        """获取客户端和配置"""
        provider = self.select_model(question)
        config = MODEL_CONFIGS[provider]
        client = self.clients.get(provider)
        
        # 如果当前 provider 没有客户端，尝试使用第一个可用的
        if client is None:
            provider = list(self.clients.keys())[0]
            config = MODEL_CONFIGS[provider]
            client = self.clients[provider]
            print(f"[路由降级] 使用备选模型: {provider.value}")
        
        # 更新统计
        self.stats["total_requests"] += 1
        provider_value = provider.value if hasattr(provider, 'value') else str(provider)
        self.stats["model_usage"][provider_value] = self.stats["model_usage"].get(provider_value, 0) + 1
        
        print(f"[路由执行] 使用模型: {config['name']}")
        
        return client, config
    
    def has_clients(self) -> bool:
        """检查是否有可用客户端"""
        return len(self.clients) > 0
    
    def get_stats(self) -> Dict:
        """获取路由统计信息"""
        return {
            "total_requests": self.stats["total_requests"],
            "model_usage": self.stats["model_usage"],
            "fallback_count": self.stats["fallback_count"],
            "available_models": [p.value if hasattr(p, 'value') else str(p) for p in self.clients.keys()],
        }
    
    def chat(self, messages: List[Dict], **kwargs) -> Any:
        """智能路由对话"""
        # 获取用户最后一条消息
        user_message = ""
        for m in reversed(messages):
            if m["role"] == "user":
                user_message = m["content"]
                break
        
        # 选择模型并调用
        try:
            client, config = self._get_client_and_config(user_message)
        except Exception as e:
            print(f"[路由错误] {e}")
            return self._fallback_chat(messages, **kwargs)
        
        try:
            response = client.chat.completions.create(
                model=config["name"],
                messages=messages,
                **kwargs
            )
            return response
        except Exception as e:
            print(f"[路由调用错误] {e}")
            return self._fallback_chat(messages, **kwargs)
    
    def _fallback_chat(self, messages: List[Dict], **kwargs) -> Any:
        """降级方案：尝试其他模型"""
        self.stats["fallback_count"] += 1
        
        for provider, client in self.clients.items():
            try:
                config = MODEL_CONFIGS[provider]
                print(f"[降级] 尝试使用 {config['name']}")
                response = client.chat.completions.create(
                    model=config["name"],
                    messages=messages,
                    **kwargs
                )
                return response
            except Exception as e:
                print(f"[降级失败] {config['name']}: {e}")
                continue
        
        raise Exception("所有模型都调用失败")
    
    def chat_stream(self, messages: List[Dict], **kwargs) -> Generator:
        """智能路由流式对话"""
        user_message = ""
        for m in reversed(messages):
            if m["role"] == "user":
                user_message = m["content"]
                break
        
        try:
            client, config = self._get_client_and_config(user_message)
        except Exception as e:
            print(f"[路由错误] {e}")
            yield from self._fallback_chat_stream(messages, **kwargs)
            return
        
        try:
            stream = client.chat.completions.create(
                model=config["name"],
                messages=messages,
                stream=True,
                **kwargs
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            print(f"[路由流式错误] {e}")
            yield from self._fallback_chat_stream(messages, **kwargs)
    
    def _fallback_chat_stream(self, messages: List[Dict], **kwargs) -> Generator:
        """降级流式方案"""
        for provider, client in self.clients.items():
            try:
                config = MODEL_CONFIGS[provider]
                print(f"[降级流式] 尝试使用 {config['name']}")
                stream = client.chat.completions.create(
                    model=config["name"],
                    messages=messages,
                    stream=True,
                    **kwargs
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return
            except Exception as e:
                print(f"[降级流式失败] {config['name']}: {e}")
                continue
        
        yield "所有模型都调用失败，请稍后再试。"


# 全局路由器实例
_router = None


def get_router() -> LLMRouter:
    """获取路由器单例"""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


# 便捷函数
def chat_with_router(messages: List[Dict], **kwargs) -> Any:
    """使用路由器的快捷函数"""
    return get_router().chat(messages, **kwargs)


def chat_stream_with_router(messages: List[Dict], **kwargs) -> Generator:
    """使用路由器的快捷流式函数"""
    return get_router().chat_stream(messages, **kwargs)