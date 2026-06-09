"""自然语言转 SQL - 核心亮点功能"""
import json
import re
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
    """自然语言转 SQL 引擎"""
    
    def __init__(self, df: pd.DataFrame, table_name: str = "sales_data"):
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
                self.column_types[col] = "string"
        
        # 样例数据
        self.sample_data = df.head(3).to_dict(orient="records")
        
        # 统计信息（用于智能查询）
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
                    "unique_values": self.df[col].nunique(),
                    "top_values": self.df[col].value_counts().head(5).to_dict()
                }
        return stats
    
    def parse(self, natural_language: str) -> Dict[str, Any]:
        """将自然语言解析为查询结构"""
        
        system_prompt = f"""你是一个数据分析专家。根据用户的自然语言问题，将问题转换为结构化的查询参数。

## 数据表信息
- 表名: {self.table_name}
- 列名: {self.columns}
- 列类型: {json.dumps(self.column_types, ensure_ascii=False)}
- 数据统计: {json.dumps(self.stats, ensure_ascii=False, default=str)}
- 样例数据: {json.dumps(self.sample_data, ensure_ascii=False)}

## 返回格式（JSON）
{{
    "query_type": "select/count/sum/avg/max/min/group_by/top",
    "select_columns": ["列名1", "列名2"],  // 要查询的列
    "filters": [
        {{"column": "列名", "operator": "=/contains/</>", "value": "值"}}
    ],
    "group_by": ["列名"],  // 分组字段
    "aggregate": {{"function": "sum/avg/count/max/min", "column": "列名"}},
    "order_by": {{"column": "列名", "direction": "asc/desc"}},
    "limit": 数字,
    "explanation": "对用户问题的解释"
}}

## 示例
用户: "哪个产品卖得最好？"
返回: {{
    "query_type": "top",
    "group_by": ["产品"],
    "aggregate": {{"function": "sum", "column": "销售额"}},
    "order_by": {{"column": "销售额", "direction": "desc"}},
    "limit": 1,
    "explanation": "按产品分组求和销售额，降序取第一个"
}}

用户: "张三的总销售额是多少？"
返回: {{
    "query_type": "sum",
    "filters": [{{"column": "销售员", "operator": "=", "value": "张三"}}],
    "aggregate": {{"function": "sum", "column": "销售额"}},
    "explanation": "筛选销售员为张三，计算销售额总和"
}}

用户: "最近一周的销售趋势"
返回: {{
    "query_type": "group_by",
    "group_by": ["日期"],
    "select_columns": ["日期", "销售额"],
    "order_by": {{"column": "日期", "direction": "asc"}},
    "explanation": "按日期分组查看销售额趋势"
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
            
            result = json.loads(response.choices[0].message.content)
            print(f"📝 解析结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return result
            
        except Exception as e:
            print(f"解析失败: {e}")
            return {"error": str(e), "query_type": "error"}
    
    def execute(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """执行查询并返回结果"""
        if query.get("error"):
            return {"success": False, "error": query["error"]}
        
        df = self.df.copy()
        
        # 1. 应用筛选条件
        for filter_item in query.get("filters", []):
            column = filter_item["column"]
            operator = filter_item["operator"]
            value = filter_item["value"]
            
            if column not in df.columns:
                continue
            
            if operator == "=":
                df = df[df[column].astype(str) == str(value)]
            elif operator == "contains":
                df = df[df[column].astype(str).str.contains(str(value), case=False)]
            elif operator == ">":
                df = df[df[column] > float(value)]
            elif operator == "<":
                df = df[df[column] < float(value)]
        
        # 2. 分组聚合
        group_by = query.get("group_by", [])
        aggregate = query.get("aggregate", {})
        
        if group_by and aggregate:
            func = aggregate.get("function", "sum")
            col = aggregate.get("column")
            
            if col and col in df.columns:
                if func == "sum":
                    result_df = df.groupby(group_by)[col].sum().reset_index()
                elif func == "avg":
                    result_df = df.groupby(group_by)[col].mean().reset_index()
                elif func == "count":
                    result_df = df.groupby(group_by)[col].count().reset_index()
                elif func == "max":
                    result_df = df.loc[df.groupby(group_by)[col].idxmax()]
                elif func == "min":
                    result_df = df.loc[df.groupby(group_by)[col].idxmin()]
                else:
                    result_df = df
            else:
                result_df = df
        else:
            result_df = df
        
        # 3. 选择列
        select_cols = query.get("select_columns", [])
        if select_cols:
            existing_cols = [c for c in select_cols if c in result_df.columns]
            if existing_cols:
                result_df = result_df[existing_cols]
        
        # 4. 排序
        order_by = query.get("order_by", {})
        if order_by.get("column") and order_by["column"] in result_df.columns:
            direction = order_by.get("direction", "asc")
            result_df = result_df.sort_values(order_by["column"], ascending=(direction == "asc"))
        
        # 5. 限制条数
        limit = query.get("limit")
        if limit:
            result_df = result_df.head(limit)
        
        # 6. 生成回答
        result_data = result_df.to_dict(orient="records")
        
        return {
            "success": True,
            "query_type": query.get("query_type"),
            "explanation": query.get("explanation", ""),
            "result": result_data,
            "row_count": len(result_data),
            "columns": list(result_df.columns)
        }
    
    def ask(self, question: str) -> Dict[str, Any]:
        """完整问答流程：解析 + 执行 + 生成回答"""
        # 1. 解析自然语言
        parsed = self.parse(question)
        
        if parsed.get("error"):
            return {
                "success": False,
                "answer": f"解析失败: {parsed['error']}",
                "sql": None,
                "data": None
            }
        
        # 2. 执行查询
        result = self.execute(parsed)
        
        if not result["success"]:
            return {
                "success": False,
                "answer": f"查询失败: {result.get('error', '未知错误')}",
                "sql": None,
                "data": None
            }
        
        # 3. 用 LLM 生成自然语言回答
        answer = self._generate_answer(question, parsed, result)
        
        return {
            "success": True,
            "answer": answer,
            "query_info": {
                "type": parsed.get("query_type"),
                "explanation": parsed.get("explanation")
            },
            "data": result["result"],
            "row_count": result["row_count"]
        }
    
    def _generate_answer(self, question: str, parsed: Dict, result: Dict) -> str:
        """生成自然语言回答"""
        prompt = f"""
根据查询结果回答用户问题。

用户问题: {question}
查询解释: {parsed.get('explanation', '')}
查询结果: {json.dumps(result['result'], ensure_ascii=False, default=str)}

要求：
1. 用简洁的中文回答
2. 直接给出答案，不要重复问题
3. 如果是数字，格式化显示（如 87000 显示为 87,000）
4. 如果是列表，用编号列出

回答:
"""
        try:
            response = client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            return response.choices[0].message.content
        except:
            # 降级方案：直接返回数据
            if result["result"]:
                return json.dumps(result["result"], ensure_ascii=False, indent=2)
            return "没有找到相关数据"