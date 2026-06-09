from data_loader import execute_sql_query

# 测试基本查询
print("测试1: 基本查询")
result = execute_sql_query('SELECT * FROM sales LIMIT 5')
print(result)

print("\n测试2: 分组聚合查询")
result = execute_sql_query('SELECT 品类, SUM(销售额) as 总销售额 FROM sales GROUP BY 品类')
print(result)

print("\n测试3: 条件查询")
result = execute_sql_query("SELECT * FROM sales WHERE 品类='电子产品'")
print(result)

print("\n测试4: 排序查询")
result = execute_sql_query('SELECT 产品, 销售额 FROM sales ORDER BY 销售额 DESC')
print(result)