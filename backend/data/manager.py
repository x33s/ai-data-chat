"""文件和数据管理 - 上传、删除、切换、预览"""
import os
import time
import pandas as pd
from io import BytesIO
from typing import List, Dict

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "uploads")
os.makedirs(DATA_DIR, exist_ok=True)

# ========== 全局状态 ==========
_data_cache = {}          # DataFrame 缓存
_current_dataset = None   # 当前激活的数据集


# ========== 文件管理 ==========
def get_all_datasets() -> List[Dict]:
    """获取所有已上传的数据集"""
    datasets = []
    if not os.path.exists(DATA_DIR):
        return datasets
    
    for filename in os.listdir(DATA_DIR):
        if not filename.endswith(('.csv', '.xlsx', '.xls')):
            continue
            
        file_path = os.path.join(DATA_DIR, filename)
        try:
            stat = os.stat(file_path)
            
            # 从缓存获取信息
            if filename in _data_cache:
                df = _data_cache[filename]
                rows, cols = len(df), len(df.columns)
            else:
                # 快速读取前1000行获取结构
                if filename.endswith('.csv'):
                    df_sample = pd.read_csv(file_path, nrows=1000)
                else:
                    df_sample = pd.read_excel(file_path, nrows=1000)
                rows, cols = len(df_sample), len(df_sample.columns)
            
            datasets.append({
                "name": filename,
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "rows": rows,
                "columns": cols,
                "is_active": filename == _current_dataset,
            })
        except Exception as e:
            print(f"获取文件信息失败 {filename}: {e}")
    
    return datasets


def save_uploaded_files(files: List) -> List[Dict]:
    """批量保存上传的文件"""
    global _data_cache, _current_dataset
    
    results = []
    
    for file in files:
        try:
            print(f"处理文件: {file.filename}")
            content = file.file.read()
            print(f"  大小: {len(content)} bytes")
            
            safe_name = file.filename.replace(" ", "_")
            file_path = os.path.join(DATA_DIR, safe_name)
            with open(file_path, "wb") as f:
                f.write(content)
            
            # 解析数据
            if safe_name.endswith('.csv'):
                df = pd.read_csv(BytesIO(content))
            else:
                df = pd.read_excel(BytesIO(content))
            
            rows, cols = len(df), len(df.columns)
            print(f"  行数: {rows}, 列数: {cols}")
            
            # 缓存
            _data_cache[safe_name] = df
            if _current_dataset is None:
                _current_dataset = safe_name
            
            # 生成预览
            preview = []
            for _, row in df.head(3).iterrows():
                row_dict = {}
                for col, val in row.items():
                    if hasattr(val, 'strftime'):
                        row_dict[col] = val.strftime('%Y-%m-%d')
                    elif pd.isna(val):
                        row_dict[col] = None
                    else:
                        row_dict[col] = val
                preview.append(row_dict)
            
            results.append({
                "success": True,
                "filename": safe_name,
                "rows": rows,
                "columns": cols,
                "preview": preview
            })
            
        except Exception as e:
            results.append({
                "success": False,
                "filename": file.filename,
                "error": str(e)
            })
    
    return results


def delete_dataset(filename: str) -> Dict:
    """删除数据集"""
    global _data_cache, _current_dataset
    
    file_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    _data_cache.pop(filename, None)
    
    if _current_dataset == filename:
        datasets = get_all_datasets()
        _current_dataset = datasets[0]["name"] if datasets else None
    
    return {"success": True}


# ========== 数据集管理 ==========
def get_current_data():
    """获取当前数据集"""
    global _current_dataset, _data_cache
    
    if _current_dataset is None:
        datasets = get_all_datasets()
        if not datasets:
            raise FileNotFoundError("没有找到数据集")
        _current_dataset = datasets[0]["name"]
    
    if _current_dataset not in _data_cache:
        # 重新加载
        file_path = os.path.join(DATA_DIR, _current_dataset)
        if _current_dataset.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        _data_cache[_current_dataset] = df
    
    return _data_cache[_current_dataset]


def get_current_data_info() -> Dict:
    """获取当前数据信息"""
    try:
        df = get_current_data()
    except Exception as e:
        return {"error": str(e)}
    
    # 识别列
    def find_col(keywords):
        for col in df.columns:
            if any(k in col.lower() for k in keywords):
                return col
        return None
    
    sales_col = find_col(['销售额', 'sales', '金额'])
    product_col = find_col(['产品', 'product', '商品'])
    sp_col = find_col(['销售员', 'salesperson', '姓名'])
    date_col = find_col(['日期', 'date'])
    
    result = {
        "filename": _current_dataset,
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
        "total_sales": float(df[sales_col].sum()) if sales_col else 0,
        "products": df[product_col].dropna().unique().tolist() if product_col else [],
        "salespersons": df[sp_col].dropna().unique().tolist() if sp_col else [],
    }
    
    if date_col:
        try:
            dates = pd.to_datetime(df[date_col], errors='coerce')
            if dates.notna().any():
                result["date_range"] = {
                    "start": dates.min().strftime('%Y-%m-%d'),
                    "end": dates.max().strftime('%Y-%m-%d')
                }
        except:
            pass
    
    return result


def switch_dataset(filename: str) -> Dict:
    """切换数据集"""
    global _current_dataset
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        return {"success": False, "error": "文件不存在"}
    
    _current_dataset = filename
    return {"success": True, "filename": filename}


def get_data_preview(limit: int = 10) -> Dict:
    """获取数据预览"""
    try:
        df = get_current_data()
    except Exception as e:
        return {"error": str(e), "preview": []}
    
    preview = []
    for _, row in df.head(limit).iterrows():
        row_dict = {}
        for col, val in row.items():
            if hasattr(val, 'strftime'):
                row_dict[col] = val.strftime('%Y-%m-%d')
            elif pd.isna(val):
                row_dict[col] = None
            else:
                row_dict[col] = val
        preview.append(row_dict)
    
    return {
        "filename": _current_dataset,
        "preview": preview,
        "total_rows": len(df),
        "total_columns": len(df.columns),
    }


# ========== 兼容接口 ==========
def load_data():
    return get_current_data()


def update_data_from_upload(content: bytes, filename: str) -> Dict:
    """更新数据（上传后）"""
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        else:
            df = pd.read_excel(BytesIO(content))
        _data_cache[filename] = df
        global _current_dataset
        _current_dataset = filename
        return {"success": True, "data": {"rows": len(df), "columns": len(df.columns)}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_uploaded_file(content: bytes, filename: str) -> Dict:
    """解析文件预览"""
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        else:
            df = pd.read_excel(BytesIO(content))
        
        preview = []
        for _, row in df.head(5).iterrows():
            row_dict = {}
            for col, val in row.items():
                if hasattr(val, 'strftime'):
                    row_dict[col] = val.strftime('%Y-%m-%d')
                elif pd.isna(val):
                    row_dict[col] = None
                else:
                    row_dict[col] = val
            preview.append(row_dict)
        
        return {
            "success": True,
            "data": {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
                "preview": preview
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}