"""查询和缓存 - 数据分析、SQL、缓存"""
import hashlib
import pandas as pd
from typing import Dict, Any

from .manager import get_current_data

# ========== 缓存 ==========
_query_cache = {}
_cache_stats = {"hits": 0, "misses": 0}


def _get_cache_key(df_hash: str, **kwargs) -> str:
    """生成缓存键"""
    key = df_hash
    for k, v in sorted(kwargs.items()):
        if v:
            key += f"|{k}={v}"
    return hashlib.md5(key.encode()).hexdigest()


def _get_df_hash(df: pd.DataFrame) -> str:
    """计算 DataFrame 哈希"""
    try:
        return hashlib.md5(pd.util.hash_pandas_object(df).values.tobytes()).hexdigest()
    except:
        return hashlib.md5(f"{len(df)}_{len(df.columns)}".encode()).hexdigest()


def get_cache_stats() -> dict:
    """获取缓存统计"""
    return {
        "size": len(_query_cache),
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "hit_rate": round(
            _cache_stats["hits"] / max(1, _cache_stats["hits"] + _cache_stats["misses"]) * 100, 1
        )
    }


def clear_cache():
    """清空缓存"""
    global _query_cache, _cache_stats
    _query_cache.clear()
    _cache_stats = {"hits": 0, "misses": 0}


# ========== 查询 ==========
def _find_column(df: pd.DataFrame, keywords: list) -> str:
    """查找匹配的列"""
    for col in df.columns:
        col_lower = col.lower()
        for kw in keywords:
            if kw in col_lower:
                return col
    return None


def query_sales_data(**kwargs) -> Dict[str, Any]:
    """查询销售数据（带缓存）"""
    try:
        df = get_current_data()
    except Exception as e:
        return {"error": str(e)}
    
    # 缓存检查
    df_hash = _get_df_hash(df)
    cache_key = _get_cache_key(df_hash, **kwargs)
    
    if cache_key in _query_cache:
        _cache_stats["hits"] += 1
        return _query_cache[cache_key]
    
    _cache_stats["misses"] += 1
    
    # 查找关键列
    sales_col = _find_column(df, ['销售额', 'sales', '金额'])
    product_col = _find_column(df, ['产品', 'product', '商品'])
    sp_col = _find_column(df, ['销售员', 'salesperson', '姓名'])
    date_col = _find_column(df, ['日期', 'date'])
    
    result = {"total_records": len(df)}
    
    if sales_col:
        result["total_sales"] = float(df[sales_col].sum())
        
        if product_col:
            product_sales = df.groupby(product_col)[sales_col].sum().to_dict()
            result["product_sales"] = {k: float(v) for k, v in product_sales.items()}
        
        if sp_col:
            sp_sales = df.groupby(sp_col)[sales_col].sum().to_dict()
            result["salesperson_sales"] = {k: float(v) for k, v in sp_sales.items()}
        
        if date_col:
            try:
                df_copy = df.copy()
                df_copy['月份'] = pd.to_datetime(df_copy[date_col], errors='coerce').dt.strftime('%Y-%m')
                monthly = df_copy.groupby('月份')[sales_col].sum().to_dict()
                result["monthly_sales"] = {k: float(v) for k, v in monthly.items() if pd.notna(k)}
            except:
                pass
    
    _query_cache[cache_key] = result
    # 限制缓存大小
    if len(_query_cache) > 100:
        keys = list(_query_cache.keys())[:20]
        for k in keys:
            del _query_cache[k]
    
    return result


def get_data_info() -> Dict:
    """获取数据概览"""
    try:
        from .manager import get_current_data_info
        return get_current_data_info()
    except Exception as e:
        return {"error": str(e)}


def execute_sql_query(sql: str) -> Dict[str, Any]:
    """执行 SQL 查询"""
    try:
        import duckdb
        df = get_current_data()
        con = duckdb.connect()
        con.register('sales', df)
        result_df = con.execute(sql).fetchdf()
        con.close()
        
        # 日期列转字符串
        for col in result_df.columns:
            if result_df[col].dtype == 'datetime64[ns]':
                result_df[col] = result_df[col].dt.strftime('%Y-%m-%d')
        
        return {
            "success": True,
            "sql": sql,
            "columns": result_df.columns.tolist(),
            "data": result_df.to_dict(orient='records'),
            "row_count": len(result_df)
        }
    except ImportError:
        return {"success": False, "error": "需要安装 duckdb: pip install duckdb"}
    except Exception as e:
        return {"success": False, "error": str(e)}