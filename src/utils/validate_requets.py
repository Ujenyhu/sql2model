import sqlparse

def validate_sql(sql: str) -> bool:
    """
    Validate SQL statement
    """
    statements = sqlparse.parse(sql)
    return any(stmt.get_type() == "CREATE" for stmt in statements)
