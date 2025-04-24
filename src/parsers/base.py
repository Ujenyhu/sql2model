import sqlparse
from abc import ABC, abstractmethod

class BaseParser(ABC):
    def __init__(self, sql: str):
        self.sql = sql
        self.cleaned_sql = self._clean_sql(sql)
        self.parsedSql = sqlparse.parse(self.cleaned_sql)
        #self.parsedSql = self._split_statements(self.cleaned_sql)


    def _clean_sql(self, sql: str) -> str:
        return sqlparse.format(sql, strip_comments=True, reindent=True)


    def _split_statements(self, sql: str) -> list:
        return sqlparse.split(sql)
    

    @abstractmethod
    def convert_to_model(self) -> str:
        pass   
    

       

