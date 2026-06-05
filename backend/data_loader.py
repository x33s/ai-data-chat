"""数据加载模块 - 支持 CSV 文件"""
import os
import pandas as pd
from typing import Dict, List, Any, Optional

# 全局数据缓存
_data_cache = None
_data_path = os.path.join(os.path.dirname(__file__), "data", "sales_data.csv")


def load_data(file_path: str = None) -> pd.DataFrame:
    """加载 CSV 数据"""
    global _data_cache
    
    if _data_cache is not None:
        return _data_cache
    
    path = file_path or _data_path
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"数据文件不存在: {path}")
    
    df = pd.read_csv(path)
    # 转换日期列
    df['日期'] = pd.to_datetime(df['日期'])
    _data_cache = df
    
    print(f"[INFO] 已加载数据: {len(df)} 行, {df.shape[1]} 列")
    print(f"   列名: {list(df.columns)}")
    
    return df


def get_data_info() -> Dict[str, Any]:
    """获取数据概览信息"""
    df = load_data()
    
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "date_range": {
            "start": df['日期'].min().strftime('%Y-%m-%d'),
            "end": df['日期'].max().strftime('%Y-%m-%d')
        },
        "products": df['产品'].unique().tolist(),
        "categories": df['品类'].unique().tolist(),
        "salespersons": df['销售员'].unique().tolist(),
        "total_sales": float(df['销售额'].sum()),
        "avg_sales": float(df['销售额'].mean())
    }


def query_sales_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    product: Optional[str] = None,
    category: Optional[str] = None,
    salesperson: Optional[str] = None
) -> Dict[str, Any]:
    """
    查询销售数据
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        product: 产品名称
        category: 品类
        salesperson: 销售员
    
    Returns:
        查询结果统计
    """
    df = load_data()
    filtered = df.copy()
    
    # 日期筛选
    if start_date:
        filtered = filtered[filtered['日期'] >= pd.to_datetime(start_date)]
    if end_date:
        filtered = filtered[filtered['日期'] <= pd.to_datetime(end_date)]
    
    # 其他筛选
    if product:
        filtered = filtered[filtered['产品'] == product]
    if category:
        filtered = filtered[filtered['品类'] == category]
    if salesperson:
        filtered = filtered[filtered['销售员'] == salesperson]
    
    if len(filtered) == 0:
        return {"message": "没有找到符合条件的数据", "data": []}
    
    # 按产品汇总销售额
    product_sales = filtered.groupby('产品')['销售额'].sum().to_dict()
    product_sales = {k: float(v) for k, v in product_sales.items()}
    
    # 按品类汇总
    category_sales = filtered.groupby('品类')['销售额'].sum().to_dict()
    category_sales = {k: float(v) for k, v in category_sales.items()}
    
    # 按销售员汇总
    salesperson_sales = filtered.groupby('销售员')['销售额'].sum().to_dict()
    salesperson_sales = {k: float(v) for k, v in salesperson_sales.items()}
    
    # 按月汇总
    filtered['月份'] = filtered['日期'].dt.strftime('%Y-%m')
    monthly_sales = filtered.groupby('月份')['销售额'].sum().to_dict()
    monthly_sales = {k: float(v) for k, v in monthly_sales.items()}
    
    return {
        "total_records": len(filtered),
        "total_sales": float(filtered['销售额'].sum()),
        "avg_sales": float(filtered['销售额'].mean()),
        "product_sales": product_sales,
        "category_sales": category_sales,
        "salesperson_sales": salesperson_sales,
        "monthly_sales": monthly_sales,
        "top_product": max(product_sales, key=product_sales.get) if product_sales else None,
        "top_salesperson": max(salesperson_sales, key=salesperson_sales.get) if salesperson_sales else None
    }


def get_chart_data(chart_type: str, data: Dict) -> Dict:
    """
    生成图表配置
    
    Args:
        chart_type: 图表类型 (bar, line, pie)
        data: 查询返回的数据
    
    Returns:
        ECharts 配置
    """
    # 优先使用产品销售额数据
    if data.get("product_sales"):
        series_data = data["product_sales"]
        title = "各产品销售额"
    elif data.get("monthly_sales"):
        series_data = data["monthly_sales"]
        title = "月度销售额趋势"
    elif data.get("salesperson_sales"):
        series_data = data["salesperson_sales"]
        title = "销售员业绩"
    else:
        return {"error": "没有可展示的数据"}
    
    x_data = list(series_data.keys())
    y_data = list(series_data.values())
    
    if chart_type == "bar":
        option = {
            "title": {"text": title},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": x_data, "name": "类别"},
            "yAxis": {"type": "value", "name": "销售额(元)"},
            "series": [{"type": "bar", "data": y_data, "name": "销售额"}]
        }
    elif chart_type == "line":
        option = {
            "title": {"text": title},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": x_data, "name": "月份"},
            "yAxis": {"type": "value", "name": "销售额(元)"},
            "series": [{"type": "line", "data": y_data, "name": "销售额", "smooth": True}]
        }
    elif chart_type == "pie":
        option = {
            "title": {"text": title},
            "tooltip": {"trigger": "item"},
            "series": [{
                "type": "pie",
                "radius": "50%",
                "data": [{"name": k, "value": v} for k, v in series_data.items()],
                "label": {"show": True}
            }]
        }
    else:
        option = {"error": f"不支持的图表类型: {chart_type}"}
    
    return option