"""数据加载模块 - 支持多文件上传、动态识别列、缓存优化"""
import os
import pandas as pd
from typing import List, Dict, Any
from io import BytesIO
import traceback
import time
import hashlib
from functools import lru_cache
from contextlib import contextmanager

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "uploads")
os.makedirs(DATA_DIR, exist_ok=True)

# 全局缓存
_data_cache = {}
_data_info_cache = {}
_current_dataset = None

# ========== 性能优化：查询缓存 ==========
_query_cache = {}
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "total_queries": 0
}

# 最大缓存数量
MAX_CACHE_SIZE = 100


def _get_cache_key(df_hash: str, **kwargs) -> str:
    """生成缓存键"""
    key_parts = [df_hash]
    for k, v in sorted(kwargs.items()):
        if v is not None:
            key_parts.append(f"{k}={v}")
    return hashlib.md5("|".join(key_parts).encode()).hexdigest()


def _get_df_hash(df: pd.DataFrame) -> str:
    """计算 DataFrame 的哈希值（用于缓存验证）"""
    try:
        # 使用 pandas 的哈希函数
        return hashlib.md5(pd.util.hash_pandas_object(df).values.tobytes()).hexdigest()
    except:
        # 降级：使用行数和列数
        return hashlib.md5(f"{len(df)}_{len(df.columns)}".encode()).hexdigest()


def _clean_old_cache():
    """清理过期缓存（保持最大数量）"""
    global _query_cache
    if len(_query_cache) > MAX_CACHE_SIZE:
        # 删除最早的 20% 缓存
        keys_to_remove = list(_query_cache.keys())[:MAX_CACHE_SIZE // 5]
        for key in keys_to_remove:
            del _query_cache[key]
        print(f"[缓存清理] 删除了 {len(keys_to_remove)} 个旧缓存")


def get_cache_stats() -> Dict:
    """获取缓存统计信息"""
    return {
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "hit_rate": round(_cache_stats["hits"] / max(1, _cache_stats["total_queries"]) * 100, 2),
        "cache_size": len(_query_cache)
    }


# ========== 错误处理装饰器 ==========
@contextmanager
def handle_errors(default_value=None, error_msg="操作失败"):
    """统一错误处理上下文管理器"""
    try:
        yield
    except FileNotFoundError as e:
        print(f"[文件错误] {e}")
        return default_value if default_value is not None else {"error": str(e)}
    except pd.errors.EmptyDataError:
        print("[数据错误] 文件为空")
        return default_value if default_value is not None else {"error": "文件为空"}
    except pd.errors.ParserError as e:
        print(f"[解析错误] {e}")
        return default_value if default_value is not None else {"error": f"文件解析失败: {str(e)}"}
    except Exception as e:
        print(f"[未知错误] {e}")
        traceback.print_exc()
        return default_value if default_value is not None else {"error": error_msg}


def safe_dataframe_operation(df: pd.DataFrame, operation: str, default_value=None):
    """安全执行 DataFrame 操作"""
    try:
        return df
    except Exception as e:
        print(f"[DataFrame操作失败] {operation}: {e}")
        return default_value if default_value is not None else pd.DataFrame()


def get_all_datasets() -> List[Dict]:
    """获取所有已上传的数据集信息（带缓存）"""
    global _current_dataset, _data_cache, _data_info_cache
    
    datasets = []
    if not os.path.exists(DATA_DIR):
        return datasets
    
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(('.csv', '.xlsx', '.xls')):
            file_path = os.path.join(DATA_DIR, filename)
            try:
                stat = os.stat(file_path)
                
                rows = 0
                columns = 0
                column_names = []
                
                if filename in _data_cache:
                    df = _data_cache[filename]
                    rows = len(df)
                    columns = len(df.columns)
                    column_names = list(df.columns)[:5]
                elif filename in _data_info_cache:
                    rows = _data_info_cache[filename].get("rows", 0)
                    columns = _data_info_cache[filename].get("columns", 0)
                    column_names = _data_info_cache[filename].get("column_names", [])
                else:
                    try:
                        # 大文件优化：超过10MB只读取前1000行获取结构
                        if stat.st_size > 10 * 1024 * 1024:  # 10MB
                            if filename.endswith('.csv'):
                                df = pd.read_csv(file_path, nrows=1000)
                            else:
                                # Excel 不支持 nrows，使用 sheet_name
                                df = pd.read_excel(file_path, nrows=1000)
                        else:
                            if filename.endswith('.csv'):
                                df = pd.read_csv(file_path)
                            else:
                                df = pd.read_excel(file_path)
                        rows = len(df)
                        columns = len(df.columns)
                        column_names = list(df.columns)[:5]
                        _data_cache[filename] = df
                        _data_info_cache[filename] = {
                            "rows": rows,
                            "columns": columns,
                            "column_names": column_names
                        }
                    except Exception as e:
                        print(f"  预加载失败: {e}")
                        pass
                
                datasets.append({
                    "name": filename,
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": stat.st_mtime,
                    "is_active": filename == _current_dataset,
                    "rows": rows,
                    "columns": columns,
                    "column_names": column_names
                })
            except Exception as e:
                print(f"获取文件信息失败 {filename}: {e}")
                datasets.append({
                    "name": filename,
                    "size": 0,
                    "is_active": filename == _current_dataset,
                    "rows": 0,
                    "columns": 0,
                    "column_names": []
                })
    
    return datasets


def save_uploaded_files(files: List) -> List[Dict]:
    """批量保存上传的文件（优化版）"""
    global _data_cache, _current_dataset, _data_info_cache, _query_cache
    
    results = []
    
    for file in files:
        start_time = time.time()
        try:
            print(f"处理文件: {file.filename}")
            
            content = file.file.read()
            file_size = len(content)
            print(f"  大小: {file_size} bytes ({file_size / 1024:.1f} KB)")
            
            safe_name = file.filename.replace(" ", "_")
            file_path = os.path.join(DATA_DIR, safe_name)
            with open(file_path, "wb") as f:
                f.write(content)
            
            # 解析数据（大文件优化）
            if safe_name.endswith('.csv'):
                # 大文件使用低内存模式
                if file_size > 10 * 1024 * 1024:
                    df = pd.read_csv(BytesIO(content), low_memory=True)
                else:
                    df = pd.read_csv(BytesIO(content))
            else:
                df = pd.read_excel(BytesIO(content))
            
            rows = len(df)
            cols = len(df.columns)
            load_time = time.time() - start_time
            print(f"  行数: {rows}, 列数: {cols}")
            print(f"  列名: {list(df.columns)}")
            print(f"  加载耗时: {load_time:.2f}s")
            
            _data_cache[safe_name] = df
            _data_info_cache[safe_name] = {
                "rows": rows,
                "columns": cols,
                "column_names": list(df.columns)[:10],
                "load_time": load_time,
                "file_size_mb": round(file_size / (1024 * 1024), 2)
            }
            
            if _current_dataset is None:
                _current_dataset = safe_name
                print(f"  激活数据集: {_current_dataset}")
            
            # 生成预览数据（优化：只取前3行）
            preview_data = []
            for _, row in df.head(3).iterrows():
                row_dict = {}
                for col, val in row.items():
                    if hasattr(val, 'strftime'):
                        row_dict[col] = val.strftime('%Y-%m-%d')
                    elif pd.isna(val):
                        row_dict[col] = None
                    else:
                        row_dict[col] = val
                preview_data.append(row_dict)
            
            results.append({
                "success": True,
                "filename": safe_name,
                "rows": rows,
                "columns": cols,
                "column_names": list(df.columns)[:10],
                "preview": preview_data,
                "load_time": load_time
            })
            
            print(f"  上传成功: {safe_name}")
            
            # 清空查询缓存（数据已变更）
            _query_cache.clear()
            _cache_stats["hits"] = 0
            _cache_stats["misses"] = 0
            
        except Exception as e:
            print(f"  错误: {str(e)}")
            traceback.print_exc()
            results.append({
                "success": False,
                "filename": file.filename,
                "error": str(e)
            })
    
    return results


def get_current_data():
    """获取当前激活的数据集 DataFrame（带重试）"""
    global _current_dataset, _data_cache
    
    if _current_dataset is None:
        datasets = get_all_datasets()
        if datasets:
            _current_dataset = datasets[0]["name"]
            print(f"自动激活数据集: {_current_dataset}")
        else:
            raise FileNotFoundError("没有找到任何数据集，请先上传文件")
    
    if _current_dataset not in _data_cache:
        # 尝试重新加载（最多3次）
        for retry in range(3):
            try:
                file_path = os.path.join(DATA_DIR, _current_dataset)
                if os.path.exists(file_path):
                    start_time = time.time()
                    if _current_dataset.endswith('.csv'):
                        df = pd.read_csv(file_path)
                    else:
                        df = pd.read_excel(file_path)
                    _data_cache[_current_dataset] = df
                    print(f"重新加载数据集 {_current_dataset} 耗时: {time.time() - start_time:.2f}s")
                    return df
            except Exception as e:
                print(f"重试 {retry + 1}/3 失败: {e}")
                time.sleep(1)
        raise FileNotFoundError(f"数据集加载失败: {_current_dataset}")
    
    return _data_cache[_current_dataset]


def get_current_data_info() -> Dict:
    """获取当前数据信息（带错误处理）"""
    global _current_dataset, _data_cache
    
    if _current_dataset is None:
        datasets = get_all_datasets()
        if datasets:
            _current_dataset = datasets[0]["name"]
            print(f"自动激活数据集: {_current_dataset}")
        else:
            return {"error": "没有激活的数据集", "message": "请先上传文件"}
    
    if _current_dataset not in _data_cache:
        return {"error": f"数据集不存在: {_current_dataset}", "message": "请重新上传文件"}
    
    try:
        df = _data_cache[_current_dataset]
        
        # 动态识别关键列
        date_col = None
        sales_col = None
        product_col = None
        salesperson_col = None
        category_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if '日期' in col_lower or 'date' in col_lower:
                date_col = col
            elif '销售额' in col_lower or 'sales' in col_lower or '金额' in col_lower:
                sales_col = col
            elif '产品' in col_lower or 'product' in col_lower or '商品' in col_lower:
                product_col = col
            elif '销售员' in col_lower or 'salesperson' in col_lower or '姓名' in col_lower:
                salesperson_col = col
            elif '品类' in col_lower or 'category' in col_lower or '类型' in col_lower:
                category_col = col
        
        result = {
            "filename": _current_dataset,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "total_sales": float(df[sales_col].sum()) if sales_col else 0,
            "products": df[product_col].dropna().unique().tolist() if product_col else [],
            "salespersons": df[salesperson_col].dropna().unique().tolist() if salesperson_col else [],
            "categories": df[category_col].dropna().unique().tolist() if category_col else [],
            "date_range": None
        }
        
        if date_col:
            try:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                min_date = df[date_col].min()
                max_date = df[date_col].max()
                if pd.notna(min_date) and pd.notna(max_date):
                    result["date_range"] = {
                        "start": min_date.strftime('%Y-%m-%d'),
                        "end": max_date.strftime('%Y-%m-%d')
                    }
            except Exception as e:
                print(f"日期范围计算失败: {e}")
        
        return result
        
    except Exception as e:
        print(f"get_current_data_info 错误: {e}")
        return {"error": str(e), "message": "数据加载失败"}


def get_data_preview(limit: int = 10) -> Dict:
    """获取数据预览（带错误处理）"""
    global _current_dataset, _data_cache
    
    if _current_dataset is None:
        datasets = get_all_datasets()
        if datasets:
            _current_dataset = datasets[0]["name"]
        else:
            return {"error": "没有激活的数据集", "preview": []}
    
    if _current_dataset not in _data_cache:
        return {"error": f"数据集不存在: {_current_dataset}", "preview": []}
    
    try:
        df = _data_cache[_current_dataset]
        
        preview_data = []
        for _, row in df.head(limit).iterrows():
            row_dict = {}
            for col, val in row.items():
                if hasattr(val, 'strftime'):
                    row_dict[col] = val.strftime('%Y-%m-%d')
                elif pd.isna(val):
                    row_dict[col] = None
                else:
                    row_dict[col] = val
            preview_data.append(row_dict)
        
        return {
            "filename": _current_dataset,
            "preview": preview_data,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "column_names": list(df.columns)
        }
    except Exception as e:
        print(f"get_data_preview 错误: {e}")
        return {"error": str(e), "preview": []}


def switch_dataset(filename: str) -> Dict:
    """切换数据集（带缓存清理）"""
    global _current_dataset, _data_cache, _query_cache
    
    if filename not in _data_cache:
        return {"success": False, "error": f"数据集不存在: {filename}"}
    
    _current_dataset = filename
    print(f"切换到数据集: {_current_dataset}")
    
    # 切换时清空查询缓存
    _query_cache.clear()
    _cache_stats["hits"] = 0
    _cache_stats["misses"] = 0
    
    return {"success": True, "filename": filename}


def delete_dataset(filename: str) -> Dict:
    """删除数据集（带缓存清理）"""
    global _current_dataset, _data_cache, _data_info_cache, _query_cache
    
    file_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    if filename in _data_cache:
        del _data_cache[filename]
    if filename in _data_info_cache:
        del _data_info_cache[filename]
    
    if _current_dataset == filename:
        datasets = get_all_datasets()
        if datasets:
            _current_dataset = datasets[0]["name"]
            print(f"自动切换到: {_current_dataset}")
        else:
            _current_dataset = None
    
    # 删除后清空查询缓存
    _query_cache.clear()
    
    return {"success": True}


# ========== 兼容原有接口（始终使用当前数据集）==========

def load_data():
    """加载数据 - 始终使用当前激活的数据集"""
    return get_current_data()


def get_data_info():
    """获取数据概览 - 始终使用当前数据集（带降级）"""
    try:
        return get_current_data_info()
    except Exception as e:
        print(f"get_data_info 错误: {e}")
        return {
            "rows": 0,
            "columns": [],
            "total_sales": 0,
            "products": [],
            "salespersons": [],
            "categories": [],
            "date_range": None
        }


def query_sales_data(**kwargs):
    """查询销售数据 - 带缓存"""
    global _cache_stats
    
    _cache_stats["total_queries"] += 1
    
    try:
        df = get_current_data()
        
        # 计算缓存键
        df_hash = _get_df_hash(df)
        cache_key = _get_cache_key(df_hash, **kwargs)
        
        # 检查缓存
        if cache_key in _query_cache:
            _cache_stats["hits"] += 1
            print(f"[缓存命中] {cache_key[:8]}...")
            return _query_cache[cache_key]
        
        _cache_stats["misses"] += 1
        print(f"[缓存未命中] {cache_key[:8]}...")
        
        # 执行查询
        result = {"total_records": len(df)}
        
        # 动态查找销售额列
        sales_col = None
        for col in df.columns:
            if '销售额' in col or 'sales' in col.lower() or '金额' in col:
                sales_col = col
                break
        
        if sales_col:
            result["total_sales"] = float(df[sales_col].sum())
            
            # 动态查找产品列
            product_col = None
            for col in df.columns:
                if '产品' in col or 'product' in col.lower() or '商品' in col:
                    product_col = col
                    break
            
            if product_col:
                product_sales = df.groupby(product_col)[sales_col].sum().to_dict()
                result["product_sales"] = {k: float(v) for k, v in product_sales.items()}
            
            # 动态查找销售员列
            salesperson_col = None
            for col in df.columns:
                if '销售员' in col or 'salesperson' in col.lower() or '姓名' in col:
                    salesperson_col = col
                    break
            
            if salesperson_col:
                salesperson_sales = df.groupby(salesperson_col)[sales_col].sum().to_dict()
                result["salesperson_sales"] = {k: float(v) for k, v in salesperson_sales.items()}
            
            # 动态查找日期列，按月分组
            date_col = None
            for col in df.columns:
                if '日期' in col or 'date' in col.lower():
                    date_col = col
                    break
            
            if date_col:
                try:
                    df_copy = df.copy()
                    df_copy['月份'] = pd.to_datetime(df_copy[date_col], errors='coerce').dt.strftime('%Y-%m')
                    monthly_sales = df_copy.groupby('月份')[sales_col].sum().to_dict()
                    result["monthly_sales"] = {k: float(v) for k, v in monthly_sales.items() if pd.notna(k)}
                except Exception as e:
                    print(f"月份分组失败: {e}")
        
        # 存入缓存
        _query_cache[cache_key] = result
        _clean_old_cache()
        
        return result
        
    except Exception as e:
        print(f"query_sales_data 错误: {e}")
        return {"total_records": 0, "product_sales": {}}


def update_data_from_upload(content: bytes, filename: str):
    """更新数据（带缓存清理）"""
    global _data_cache, _current_dataset, _query_cache
    
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        else:
            df = pd.read_excel(BytesIO(content))
        
        _data_cache[filename] = df
        _current_dataset = filename
        
        # 清空查询缓存
        _query_cache.clear()
        _cache_stats["hits"] = 0
        _cache_stats["misses"] = 0
        
        return {"success": True, "data": {"rows": len(df), "columns": len(df.columns)}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_uploaded_file(content: bytes, filename: str):
    """解析文件（带错误处理）"""
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        else:
            df = pd.read_excel(BytesIO(content))
        
        preview_data = []
        for _, row in df.head(5).iterrows():
            row_dict = {}
            for col, val in row.items():
                if hasattr(val, 'strftime'):
                    row_dict[col] = val.strftime('%Y-%m-%d')
                elif pd.isna(val):
                    row_dict[col] = None
                else:
                    row_dict[col] = val
            preview_data.append(row_dict)
        
        return {
            "success": True,
            "data": {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
                "preview": preview_data
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_sql_query(sql: str) -> Dict[str, Any]:
    """执行 SQL 查询（带错误处理）"""
    try:
        import duckdb
        df = get_current_data()
        con = duckdb.connect()
        con.register('sales', df)
        result_df = con.execute(sql).fetchdf()
        con.close()
        
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
        return {
            "success": False,
            "error": "需要安装 duckdb 才能执行 SQL 查询，请运行: pip install duckdb"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ========== 新增：缓存状态查询接口 ==========
def get_cache_status() -> Dict:
    """获取缓存状态（用于监控）"""
    return {
        "query_cache": {
            "size": len(_query_cache),
            "max_size": MAX_CACHE_SIZE,
            "stats": _cache_stats
        },
        "data_cache": {
            "size": len(_data_cache),
            "datasets": list(_data_cache.keys())
        },
        "current_dataset": _current_dataset
    }