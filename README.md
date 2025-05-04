# SQL2Model

A lightweight CLI tool to convert T‑SQL `CREATE TABLE` DDL into language‑specific model classes (C#, Python, etc.). An ideal SQL→model converter.

---

## Features

- **Multi‑file & piped input**: convert one or more `.sql` files, inline SQL, or piped stdin at once.  
- **Flexible error handling**: continue on errors by default, with optional `--fail-fast` mode.  
- **Verbose logging**: `-v` / `--verbose` for debug output.  
- **Plugin‑friendly architecture**

---




## 📦 Installation
Install from PyPI:
> **Note**: Still in active development.

```bash
pip install sql2model
```

Or get the latest development version:

```bash
pip install git+https://github.com/Ujenyhu/sql2model.git
```

---

## Quickstart

```bash
# Single file → C# model
sql2model schema.sql --lang csharp

# Multiple files → C# models
sql2model users.sql products.sql orders.sql --lang csharp

# Inline SQL string
sql2model --sql "CREATE TABLE [Users]([Id] INT NOT NULL PRIMARY KEY)" --lang csharp

# Piped via stdin
cat schema.sql | sql2model --lang csharp
```

---

 ## Options

| Flag                             | Description                                                            |
| -------------------------------- | ---------------------------------------------------------------------- |
| `-l, --lang [csharp|python]`     | **Required.** Target language                                          |
| `-s, --sql`                      | Inline SQL string (mutually exclusive with file inputs)               |
| `--fail-fast / --no-fail-fast`   | Stop on first error (`--fail-fast`) or process all (default)          |
| `-v, --verbose`                  | Enable debug logging                                                   |

---

## 💡 Supported Languages

- C#
<!-- - Python   -->
_(more coming soon...)_

---

## 🔍 Example

**SQL Input:**

```sql
CREATE TABLE [dbo].[Users] (
    [Id] INT PRIMARY KEY,
    [Username] NVARCHAR(50) NOT NULL,
    [Email] NVARCHAR(100),
    [CreatedAt] DATETIME DEFAULT GETDATE()
);
```

**Output (C#):**

```csharp
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

[Table("Users", Schema = "dbo")]
public class Users {
    [Key]
    public int Id { get; set; }

    [StringLength(50)]
    public string Username { get; set; }

    [StringLength(100)]
    public string? Email { get; set; }

    [Column(TypeName = "datetime")]
    public DateTime CreatedAt { get; set; }
}
```

---

## SQL File Formatting Guidelines

When using multiple `CREATE TABLE` statements in a single `.sql` file, **always** terminate each statement immediately after the closing parenthesis with **either**:

- A **semicolon** (`;`), or  
- A standalone `GO` on its own line  

This ensures the parser does not merge consecutive table definitions.

Also, if you are defining constraints (e.g., via ALTER TABLE) separately after a CREATE TABLE, you must place a `GO` after the table and again after the constraint block.  

```sql
CREATE TABLE Users (
  [Id]  INT PRIMARY KEY,
  [Name] NVARCHAR(50)
);  -- semicolon here

GO   -- or GO here

CREATE TABLE Bar (
  Id   INT PRIMARY KEY,
  Date DATE
)

GO

--OR

CREATE TABLE Users (
  [Id] INT PRIMARY KEY,
  [Name] NVARCHAR(50),
  [Status] VARCHAR(20) NULL,
)
GO

ALTER TABLE [dbo].[Users] ADD CONSTRAINT DF_Users_Status DEFAULT ('Active') FOR [Status];
GO

```

---

<!-- ## Future Plans

- Web-based interface
- JSON Schema output
- Plugin system for custom templates
- More language support -->

---

<!-- ## 🧪 Contributing

Contributions are welcome!

```bash
# Clone
git clone https://github.com/Ujenyhu/sql2model.git

# Install dev dependencies
pip install -r requirements.txt

# Run CLI
python -m sql2model.cli schema.sql --lang csharp
``` -->

---

## 📝 License

MIT © [Egwuda Ujenyuojo Precious](https://github.com/Ujenyhu)
