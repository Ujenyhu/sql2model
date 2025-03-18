import sqlparse
from abc import ABC, abstractmethod

class BaseParser(ABC):
    def __init__(self, sql: str):
        self.sql = sql
        self.parsedSql = sqlparse.parse(sql)

    @abstractmethod
    def parse_sql(self) -> str:
        pass    