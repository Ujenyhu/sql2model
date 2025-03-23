from parsers.base import BaseParser
import re


class CSharpParser(BaseParser):

    def convert_to_model(self):
        models = {}  
        alter_constraints = {} 
        last_table_name = None

        for stmt in self.parsedSql:
            stmt_type = stmt.get_type().upper()
            
            if stmt_type == "CREATE":

                model_text = (
                    "using System.ComponentModel;\n"
                    "using System.ComponentModel.DataAnnotations;\n"
                    "using System.ComponentModel.DataAnnotations.Schema;\n\n"
                )

                table_name, schema_name = self._extract_table_and_schema(stmt)
                schema_part = f', Schema = "{schema_name}"' if schema_name else ""
                model_text += f'[Table("{table_name}"{schema_part})]\n'
                model_text += f"public class {table_name}\n{{\n"
                
                primary_keys = self._extract_primary_keys(stmt)
                defaults = self._extract_default_constraints(stmt)
                columns = self._extract_columns(stmt)

                for col_name, col_type, params, is_nullable, default_value in columns:
                    cs_type = self._map_sql_type_to_csharp(col_type, is_nullable)
                    
                    attributes = []
                    if col_name in primary_keys:
                        attributes.append("[Key]")

                    if not is_nullable:
                        attributes.append('[Required(ErrorMessage = "Required")]')
                    
                    if any(col_type.upper().startswith(t) for t in ["DATETIME", "DATETIME2", "DATETIMEOFFSET", "SMALLDATETIME", "DECIMAL", "NUMERIC"]): 
                        attributes.append(f'[Column(TypeName = "{col_type}")]')

                    if col_type.upper() == "DATE":
                        attributes.append("[DataType(DataType.Date)]")

                    if col_type.upper() == "TIME":
                        attributes.append("[DataType(DataType.Time)]")

                    if any(col_type.upper().startswith(t) for t in ["VARCHAR", "NVARCHAR", "CHAR", "NCHAR", "TEXT", "NTEXT"]):
                        if params and params.lower() != "max":
                            attributes.append(f'[StringLength({params})]')
                    
                    # Handle default values from CREATE STATEMENT
                    if col_name in defaults:
                        attributes.append(f'[DefaultValue("{defaults[col_name]}")]')
                    elif default_value:
                        attributes.append(f'[DefaultValue("{default_value}")]')

                    # Apply any stored ALTER constraints
                    if table_name in alter_constraints and col_name in alter_constraints[table_name]:
                        attributes.append(f'[DefaultValue("{alter_constraints[table_name][col_name]}")]')

                    for attr in attributes:
                        model_text += f"    {attr}\n"
                    model_text += f"    public {cs_type} {col_name} {{ get; set; }}\n\n"
                
                model_text += "}\n\n"
                models[table_name] = model_text

            elif stmt_type == "ALTER":
                table_name, _ = self._extract_table_and_schema(stmt)
                defaults = self._extract_default_constraints(stmt)

                if table_name in models:
                    table_model = models[table_name]
                    for col, default in defaults.items():
                        
                        pattern = r"((?:\s*\[.*\]\s*\n)*)\s*public\s+(\S+)\s+" + re.escape(col) + r"\s+\{ get; set; \}"
                        
                        def replace(match):
                            attributes_block = match.group(1)
                            if "[DefaultValue(" in attributes_block:
                                return match.group(0)
                            replacedprop =  f"{attributes_block}    [DefaultValue(\"{default}\")]\n    public {match.group(2)} {col} {{ get; set; }}"
                            return replacedprop

                        table_model = re.sub(pattern, replace, table_model)
                    models[table_name] = table_model
                else:
                    # Store the constraint for later if CREATE hasn't run yet
                    if table_name not in alter_constraints:
                        alter_constraints[table_name] = {}
                    alter_constraints[table_name].update(defaults)


        csModel = "".join(models.values())
        return csModel


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
        
        
        match = re.search(r"ALTER\s+TABLE\s+\[?(\w+)\]?\.\[?(\w+)\]?", stmt.value, re.IGNORECASE)
        if match: 
            return match.group(2), match.group(1) 

        
        match = re.search(r"ALTER\s+TABLE\s+\[?(\w+)\]?", stmt.value, re.IGNORECASE)
        if match:
            return match.group(1), "dbo"
        
        return "UnknownTable", "dbo"


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

        # Inline default constraints
        inline_default_pattern = re.compile(
            r'DEFAULT\s+\(?\s*(?P<default>NULL|["\']?.+?["\']?)\s*\)?\s+FOR\s+\[(?P<col>\w+)\]',
            re.IGNORECASE
        )

        # Separate default constraints (ALTER TABLE constraints)
        constraint_default_pattern = re.compile(
            r'CONSTRAINT\s+\[?\w+\]?\s+DEFAULT\s+(?P<default>["\']?.+?["\']?)\s+FOR\s+\[(?P<col>\w+)\]',
            re.IGNORECASE
        )

        # Search for inline default constraints
        for match in inline_default_pattern.finditer(stmt.value):
            col = match.group("col")
            default_val = match.group("default")
            defaults[col] = default_val

        # Search for separate ALTER TABLE constraints
        for match in constraint_default_pattern.finditer(stmt.value):
            col = match.group("col")
            default_val = match.group("default")
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

