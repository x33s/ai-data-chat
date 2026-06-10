"""自然语言转 SQL - 核心亮点功能"""
import json
import pandas as pd
from typing import Dict, Any, List, Optional
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


class NLToSQL:
    """自然语言转 SQL 引擎 - 面试亮点"""
    
    def __init__(self, df: pd.DataFrame, table_name: str = "sales"):
        self.df = df
        self.table_name = table_name
        self.columns = list(df.columns)
        
        # 自动识别列的类型
        self.column_types = {}
        for col in self.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                self.column_types[col] = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                self.column_types[col] = "date"
            else:
                # 尝试判断是否为数值型字符串
                try:
                    pd.to_numeric(df[col])
                    self.column_types[col] = "numeric"
                except:
                    self.column_types[col] = "string"
        
        # 样例数据
        self.sample_data = df.head(3).to_dict(orient="records")
        
        # 统计信息
        self.stats = self._calculate_stats()
    
    def _calculate_stats(self) -> Dict:
        """计算数据统计信息"""
        stats = {}
        for col in self.columns:
            if self.column_types[col] == "numeric":
                stats[col] = {
                    "min": float(self.df[col].min()),
                    "max": float(self.df[col].max()),
                    "mean": float(self.df[col].mean()),
                    "sum": float(self.df[col].sum())
                }
            elif self.column_types[col] == "string":
                stats[col] = {
                    "unique_count": int(self.df[col].nunique()),
                    "top_values": {k: int(v) for k, v in self.df[col].value_counts().head(3).to_dict().items()}
                }
        return stats
    
    def parse(self, natural_language: str) -> Dict[str, Any]:
        """将自然语言解析为查询结构"""
        
        system_prompt = f"""你是数据分析专家。根据用户问题，转换为查询参数。

## 数据表: {self.table_name}
- 列名: {self.columns}
- 列类型: {json.dumps(self.column_types, ensure_ascii=False)}
- 数据统计: {json.dumps(self.stats, ensure_ascii=False, default=str)}
- 样例: {json.dumps(self.sample_data, ensure_ascii=False)}

## 返回 JSON:
{{
    "query_type": "select/count/sum/avg/max/min/top",
    "select_columns": ["列名"],
    "filters": [{{"column": "列名", "operator": "=/contains/</>", "value": "值"}}],
    "group_by": ["列名"],
    "aggregate": {{"function": "sum/avg/count/max/min", "column": "列名"}},
    "order_by": {{"column": "列名", "direction": "asc/desc"}},
    "limit": 数字,
    "explanation": "解释"
}}

用户: "{natural_language}"
"""
        try:
            response = client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": system_prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"error": str(e), "query_type": "error"}
    
    def execute(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """执行查询"""
        if query.get("error"):
            return {"success": False, "error": query["error"]}
        
        df = self.df.copy()
        
        # 应用筛选
        for f in query.get("filters", []):
            col, op, val = f["column"], f["operator"], f["value"]
            if col not in df.columns:
                continue
            if op == "=":
                df = df[df[col].astype(str) == str(val)]
            elif op == "contains":
                df = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]
            elif op == ">":
                df = df[pd.to_numeric(df[col], errors='coerce') > float(val)]
            elif op == "<":
                df = df[pd.to_numeric(df[col], errors='coerce') < float(val)]
        
        # 分组聚合
        group_by = query.get("group_by", [])
        agg = query.get("aggregate", {})
        
        if group_by and agg:
            func, col = agg.get("function"), agg.get("column")
            if col and col in df.columns:
                if func == "sum":
                    result = df.groupby(group_by)[col].sum().reset_index()
                elif func == "avg":
                    result = df.groupby(group_by)[col].mean().reset_index()
                elif func == "count":
                    result = df.groupby(group_by)[col].count().reset_index()
                elif func == "max":
                    result = df.loc[df.groupby(group_by)[col].idxmax()]
                elif func == "min":
                    result = df.loc[df.groupby(group_by)[col].idxmin()]
                else:
                    result = df
            else:
                result = df
        else:
            result = df
        
        # 选列
        select_cols = query.get("select_columns", [])
        if select_cols:
            exist = [c for c in select_cols if c in result.columns]
            if exist:
                result = result[exist]
        
        # 排序
        order = query.get("order_by", {})
        if order.get("column") and order["column"] in result.columns:
            result = result.sort_values(order["column"], ascending=(order.get("direction", "asc") == "asc"))
        
        # 限制
        if query.get("limit"):
            result = result.head(query["limit"])
        
        return {
            "success": True,
            "query_type": query.get("query_type"),
            "explanation": query.get("explanation", ""),
            "data": result.to_dict(orient="records"),
            "row_count": len(result),
            "columns": list(result.columns)
        }
    
    def ask(self, question: str) -> Dict[str, Any]:
        """完整问答"""
        parsed = self.parse(question)
        
        if parsed.get("error"):
            return {"success": False, "answer": f"解析失败: {parsed['error']}"}
        
        result = self.execute(parsed)
        
        if not result["success"]:
            return {"success": False, "answer": f"查询失败: {result.get('error')}"}
        
        # 生成自然语言回答
        answer = self._to_natural_language(question, parsed, result)
        
        return {
            "success": True,
            "answer": answer,
            "query_info": {"type": parsed.get("query_type"), "explanation": parsed.get("explanation")},
            "data": result["data"],
            "row_count": result["row_count"]
        }
    
    def _to_natural_language(self, question: str, parsed: Dict, result: Dict) -> str:
        """生成自然语言回答"""
        if not result["data"]:
            return "没有找到相关数据。"
        
        # 简单格式化，不额外调用 LLM
        data = result["data"][0] if result["data"] else {}
        
        if parsed.get("query_type") == "top":
            key = list(data.keys())[0] if data else ""
            val = list(data.values())[0] if data else ""
            return f"{key} 是最高的，值为 {self._format_number(val)}。"
        
        if parsed.get("query_type") in ["sum", "avg", "max", "min", "count"]:
            val = list(data.values())[0] if data else 0
            return f"{parsed['explanation']}：{self._format_number(val)}。"
        
        if result["row_count"] <= 10:
            return f"查询到 {result['row_count']} 条数据：\n" + json.dumps(result["data"], ensure_ascii=False, indent=2)
        
        return f"查询到 {result['row_count']} 条数据，前5条：\n" + json.dumps(result["data"][:5], ensure_ascii=False, indent=2)
    
    def _format_number(self, val) -> str:
        """格式化数字"""
        try:
            if isinstance(val, (int, float)):
                return f"{val:,.0f}" if val >= 1000 else str(val)
        except:
            pass
        return str(val)


# 全局实例
_nl_sql = None

def get_nl_to_sql():
    """获取 NLToSQL 实例（使用当前数据集）"""
    global _nl_sql
    try:
        from data_loader import get_current_data
        df = get_current_data()
        if df is not None:
            _nl_sql = NLToSQL(df, table_name="sales")
        return _nl_sql
    except Exception as e:
        print(f"获取 NLToSQL 失败: {e}")
        return None