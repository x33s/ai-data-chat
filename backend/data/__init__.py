"""数据模块 - 统一导出入口"""
from .manager import (
    DATA_DIR,
    get_all_datasets,
    save_uploaded_files,
    delete_dataset,
    get_current_data,
    get_current_data_info,
    switch_dataset,
    get_data_preview,
    load_data,
    update_data_from_upload,
    parse_uploaded_file,
)
from .queries import (
    query_sales_data,
    get_data_info,
    execute_sql_query,
    get_cache_stats,
    clear_cache,
)

__all__ = [
    # 文件管理
    "DATA_DIR",
    "get_all_datasets",
    "save_uploaded_files", 
    "delete_dataset",
    # 数据集管理
    "get_current_data",
    "get_current_data_info", 
    "switch_dataset",
    "get_data_preview",
    "load_data",
    "update_data_from_upload",
    "parse_uploaded_file",
    # 查询
    "query_sales_data",
    "get_data_info", 
    "execute_sql_query",
    "get_cache_stats",
    "clear_cache",
]