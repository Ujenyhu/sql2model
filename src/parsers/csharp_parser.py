from parsers.base import BaseParser
import re


class CSharpParser(BaseParser):

    def convert_to_model(self):
        model = (
            "using System.ComponentModel;\n"
            "using System.ComponentModel.DataAnnotations;\n"
            "using System.ComponentModel.DataAnnotations.Schema;\n\n"
        )

        for stmt in self.parsedSql:
            if stmt.get_type().upper() == "CREATE":
                table_name, schema_name = self._extract_table_and_schema(stmt)
                schema_part = f', Schema = "{schema_name}"' if schema_name else ""
                model += f'[Table("{table_name}"{schema_part})]\n'
                model += f"public class {table_name}\n{{\n"
                
                primary_keys = self._extract_primary_keys(stmt)
                defaults = self._extract_default_constraints(stmt)
                
                columns = self._extract_columns(stmt)
                for col_name, col_type, params, is_nullable, default_value in columns:
                    cs_type = self._map_sql_type_to_csharp(col_type, is_nullable)
                    
                    attributes = []
                    if col_name in primary_keys:
                        attributes.append("[Key]")

                    if not is_nullable:
                        attributes.append(f'[Required(ErrorMessage = "Required")]')
                    
                    
                    if any(col_type.upper().startswith(t) for t in ["DATETIME", "DATETIME2", "DATETIMEOFFSET", "SMALLDATETIME", "DECIMAL", "NUMERIC"]): 
                        attributes.append(f'[Column(TypeName = "{col_type}")]')

                    if col_type.upper() == "DATE":
                        attributes.append("[DataType(DataType.Date)]")

                    if col_type.upper() == "TIME":
                        attributes.append("[DataType(DataType.Time)]")

                    # String length annotation for string-like types
                    if any(col_type.upper().startswith(t) for t in ["VARCHAR", "NVARCHAR", "CHAR", "NCHAR", "TEXT", "NTEXT"]):
                        if params and params.lower() != "max":
                            attributes.append(f'[StringLength({params})]')
                        

                    # Handle default values
                    if col_name in defaults:
                        attributes.append(f'[DefaultValue("{defaults[col_name]}")]')
                    elif default_value:
                        attributes.append(f'[DefaultValue("{default_value}")]')
                    
                    for attr in attributes:
                        model += f"    {attr}\n"
                    model += f"    public {cs_type} {col_name} {{ get; set; }}\n\n"
                    
                model += "}\n\n"
        return model


    def _extract_table_and_schema(self, stmt) -> tuple:
        
        match = re.search(r"CREATE\s+TABLE\s+\[?(\w+)\]?\.\[?(\w+)\]?", stmt.value, re.IGNORECASE)
        if match:
            schema_name = match.group(1)
            table_name = match.group(2)
            return table_name, schema_name
        
        match = re.search(r"CREATE\s+TABLE\s+\[?(\w+)\]?", stmt.value, re.IGNORECASE)
        if match:
            table_name = match.group(1)
            return table_name, "dbo"
        return "TableName", "dbo"


    def _extract_primary_keys(self, stmt) -> set:
        primary_keys = set()
        
        pk_pattern = re.compile(
            r"PRIMARY\s+KEY\s*(?:CLUSTERED|NONCLUSTERED)?\s*\((.*?)\)",
            re.IGNORECASE | re.DOTALL
        )
        match = pk_pattern.search(stmt.value)
        if match:
            keys_str = match.group(1)
            keys = re.findall(r"\[(\w+)\]", keys_str)
            primary_keys.update(keys)
        return primary_keys



    def _extract_columns(self, stmt) -> list:
        columns = []

        column_pattern = re.compile(
            r'^\s*\[(?P<name>\w+)\]\s+\[(?P<type>\w+)\](?:\((?P<params>[^\)]+)\))?\s*(?P<nullability>NULL|NOT NULL)?',
            re.IGNORECASE
        )
        
        default_pattern = re.compile(r"DEFAULT\s+(?P<default>\S+)", re.IGNORECASE)
        
        for line in stmt.value.splitlines():
            line = line.strip()
           
            if not line.startswith("["):
                continue
            if "CONSTRAINT" in line.upper():
                continue
            match = column_pattern.match(line)
            if match:
                col_name = match.group("name")
                col_type = match.group("type")
                params = match.group("params")
                if params:
                    col_type = f"{col_type}({params})"

                nullability = match.group("nullability")
                is_nullable = True
                if nullability and "NOT NULL" in nullability.upper():
                    is_nullable = False
                    
                default_value = None
                default_match = default_pattern.search(line)
                if default_match:
                    default_value = default_match.group("default")
                columns.append((col_name, col_type, params, is_nullable, default_value))
        return columns
    


    def _extract_default_constraints(self, stmt) -> dict:
        defaults = {}
        # Inline default constraints (fixed regex)
        inline_default_pattern = re.compile(
            r'\[(?P<col>\w+)\].*DEFAULT\s+(?P<default>["\']?.+?["\']?)',
            re.IGNORECASE
        )

        # Separate default constraints (fixed regex)
        constraint_default_pattern = re.compile(
            r'CONSTRAINT\s+\[?\w+\]?\s+DEFAULT\s+(?P<default>["\']?.+?["\']?)\s+FOR\s+\[(?P<col>\w+)\]',
            re.IGNORECASE
        )
        
        for line in stmt.value.splitlines():
            inline_match = inline_default_pattern.search(line)
            if inline_match:
                col = inline_match.group("col")
                default_val = inline_match.group("default")
                defaults[col] = default_val

            constraint_match = constraint_default_pattern.search(line)
            if constraint_match:
                col = constraint_match.group("col")
                default_val = constraint_match.group("default")
                defaults[col] = default_val

        return defaults



    def _map_sql_type_to_csharp(self, sql_type: str, is_nullable: bool) -> str:
        
        base_type = re.split(r"\(", sql_type)[0].upper()
        type_map = {
            "INT": "int",
            "BIGINT": "long",
            "SMALLINT": "short",
            "TINYINT": "byte",
            "BIT": "bool",
            "DECIMAL": "decimal",
            "NUMERIC": "decimal",
            "FLOAT": "float",
            "REAL": "float",
            "MONEY": "decimal",
            "SMALLMONEY": "decimal",
            "DATE": "DateTime",
            "DATETIME": "DateTime",
            "DATETIME2": "DateTime",
            "DATETIMEOFFSET": "DateTimeOffset",
            "SMALLDATETIME": "DateTime",
            "TIME": "TimeSpan",
            "CHAR": "string",
            "VARCHAR": "string",
            "NCHAR": "string",
            "NVARCHAR": "string",
            "TEXT": "string",
            "NTEXT": "string",
            "BINARY": "byte[]",
            "VARBINARY": "byte[]",
            "IMAGE": "byte[]"
        }
        cs_type = type_map.get(base_type, "string")
       
        if is_nullable and cs_type not in ["byte[]"]:
            cs_type += "?"
        return cs_type

