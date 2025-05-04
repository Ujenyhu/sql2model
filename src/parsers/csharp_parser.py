from parsers.base import BaseParser
import re

class CSharpParser(BaseParser):

    def convert_to_model(self):
        models = {}
        # Build full script text to capture separate ALTER TABLE defaults
        full_sql = "\n".join(stmt.value for stmt in self.parsedSql)

        for stmt in self.parsedSql:
            stmt_type = stmt.get_type().upper()

            if stmt_type == "CREATE":
                # Header usings
                model_text = (
                    "using System.ComponentModel;\n"
                    "using System.ComponentModel.DataAnnotations;\n"
                    "using System.ComponentModel.DataAnnotations.Schema;\n\n"
                )

                # Table name & schema
                table_name, schema_name = self._extract_table_and_schema(stmt)
                schema_part = f', Schema = "{schema_name}"' if schema_name else ""
                model_text += f'[Table("{table_name}"{schema_part})]\n'
                model_text += f"public class {table_name}\n{{\n"

                # Extract primary keys
                primary_keys = self._extract_primary_keys(stmt)
                # Extract all columns (inline + ALTER defaults)
                columns = self._extract_columns(stmt.value, full_sql)

                # Build properties
                for name, full_type, is_nullable, default_val in columns:
                    cs_type = self._map_sql_type_to_csharp(full_type, is_nullable)

                    attrs = []
                    if name in primary_keys:
                        attrs.append("[Key]")
                    if not is_nullable:
                        attrs.append('[Required(ErrorMessage = "Required")]')
                    # Column type attributes
                    if any(full_type.upper().startswith(t) for t in ["DATETIME", "DATETIME2", "DATETIMEOFFSET", "SMALLDATETIME", "DECIMAL", "NUMERIC"]):
                        attrs.append(f'[Column(TypeName = "{full_type}")]')
                    if full_type.upper() == "DATE":
                        attrs.append("[DataType(DataType.Date)]")
                    if full_type.upper() == "TIME":
                        attrs.append("[DataType(DataType.Time)]")
                    if any(full_type.upper().startswith(t) for t in ["VARCHAR", "NVARCHAR", "CHAR", "NCHAR", "TEXT", "NTEXT"]):
                        # Use length if specified
                        m = re.search(r"\((\d+)\)", full_type)
                        if m and m.group(1).lower() != "max":
                            attrs.append(f'[StringLength({m.group(1)})]')

                    # Default value
                    if default_val is not None:
                        attrs.append(f'[DefaultValue("{default_val}")]')

                    # Append attributes & property
                    for a in attrs:
                        model_text += f"    {a}\n"
                    model_text += f"    public {cs_type} {name} {{ get; set; }}\n\n"

                model_text += "}\n\n"
                models[table_name] = model_text

        # Combine all models
        return "".join(models.values())


    def _extract_table_and_schema(self, stmt) -> tuple:
        
        match = re.search(r"CREATE\s+TABLE\s+\[?(\w+)\]?\.\[?(\w+)\]?", stmt.value, re.IGNORECASE)
        if match:
            return match.group(2), match.group(1)
        match = re.search(r"CREATE\s+TABLE\s+\[?(\w+)\]?", stmt.value, re.IGNORECASE)
        if match:
            return match.group(1), "dbo"
        # Fallback
        return "UnknownTable", "dbo"


    def _extract_primary_keys(self, stmt) -> set:
        primary_keys = set()
        pk_pattern = re.compile(r"PRIMARY\s+KEY[^(]*\((.*?)\)", re.IGNORECASE | re.DOTALL)
        inline_pattern = re.compile(r"\[(?P<col>\w+)\].*?PRIMARY\s+KEY", re.IGNORECASE)
        m = pk_pattern.search(stmt.value)
        if m:
            primary_keys.update(re.findall(r"\[(\w+)\]", m.group(1)))
        for m in inline_pattern.finditer(stmt.value):
            primary_keys.add(m.group('col'))
        return primary_keys


    def _split_columns(self, cols_text: str) -> list:
        segments, depth, start = [], 0, 0
        for i, ch in enumerate(cols_text):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch == ',' and depth == 0:
                segments.append(cols_text[start:i].strip())
                start = i + 1
        segments.append(cols_text[start:].strip())
        return segments


    def _extract_default_constraints(self, sql_text: str) -> dict:
        # Scan for ALTER TABLE ... ADD CONSTRAINT ... DEFAULT ... FOR [col]
        pat = re.compile(
            r"ALTER\s+TABLE\s+(?:\[[^\]]+\]\.)?\[[^\]]+\]\s+ADD\s+CONSTRAINT\s+\[[^\]]+\]\s+DEFAULT\s*\(?\s*(?P<def>[^)]+?)\s*\)?\s+FOR\s+\[(?P<col>\w+)\]",
            re.IGNORECASE
        )
        defaults = {}
        for m in pat.finditer(sql_text):
            defaults[m.group('col')] = m.group('def').strip(" '\"")
        return defaults



    def _extract_columns(self, create_stmt: str, full_sql: str) -> list:
        # Map of ALTER defaults
        defaults_map = self._extract_default_constraints(full_sql)
        
        # Extract only CREATE TABLE block
        #m = re.search(r"CREATE\s+TABLE[^(]*\((?P<cols>.*)\)\s*(?:ON|GO)", create_stmt, re.DOTALL | re.IGNORECASE)

        
        m = re.search( r"CREATE\s+TABLE[^(]*\((?P<cols>.*?)\)\s*(?=ON\b|GO\b|;)", create_stmt, re.DOTALL | re.IGNORECASE)
        if not m:
            return []
        cols_block = m.group('cols')
        cols = []
        for seg in self._split_columns(cols_block):
            up = seg.strip().upper()
            # skip constraints
            if not seg or up.startswith('CONSTRAINT') or up.startswith('PRIMARY KEY') or up.startswith('FOREIGN KEY'):
                continue
            cm = re.match(
                r"^\[?(?P<name>\w+)\]?\s+\[?(?P<type>\w+)\]?(?:\((?P<params>[^)]+)\))?"
                r"(?:\s+(?P<null>NOT NULL|NULL))?(?:.*?DEFAULT\s+(?P<inline>\([^)]*\)|'[^']*'|\w+))?",
                seg, re.IGNORECASE
            )
            if not cm:
                continue
            name = cm.group('name')
            typ = cm.group('type')
            params = cm.group('params')
            full_type = typ + (f"({params})" if params else "")
            is_null = not cm.group('null') or 'NULL' in cm.group('null').upper()
            # Inline default
            inline = cm.group('inline')
            default = inline.strip("() '") if inline else defaults_map.get(name)
            cols.append((name, full_type, is_null, default))
        
        return cols


    def _map_sql_type_to_csharp(self, sql_type: str, is_nullable: bool) -> str:

        base = sql_type.split('(')[0].upper()
        m = {
            "INT": "int", "BIGINT": "long", "SMALLINT": "short", "TINYINT": "byte",
            "BIT": "bool", "DECIMAL": "decimal", "NUMERIC": "decimal", "FLOAT": "float",
            "REAL": "float", "MONEY": "decimal", "SMALLMONEY": "decimal",
            "DATE": "DateTime", "DATETIME": "DateTime", "DATETIME2": "DateTime",
            "DATETIMEOFFSET": "DateTimeOffset", "SMALLDATETIME": "DateTime",
            "TIME": "TimeSpan", "CHAR": "string", "VARCHAR": "string",
            "NCHAR": "string", "NVARCHAR": "string", "TEXT": "string", "NTEXT": "string",
            "BINARY": "byte[]", "VARBINARY": "byte[]", "IMAGE": "byte[]"
        }.get(base, "string")
        return m + ('?' if is_nullable and m not in ['byte[]'] else '')
