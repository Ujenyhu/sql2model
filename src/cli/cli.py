import click
from utils.var_helper import SupportedLanguages

@click.command()
@click.argument("sql_file", required=False, type=click.File("r"))
@click.option("--sql", type=str, help="SQL statement to convert to model")
@click.option("--lang", "-l", type=click.Choice(["python", "csharp"]), required=True, help="Programming language you want a model for")

def main(sql_file, sql, lang):
   if not sql_file and not sql:
        raise click.UsageError("You must provide either an SQL file or an SQL statement.")
   
   #Read from file if provided
   sql_statement = sql if sql else sql_file.read()

   if not sql_statement:
        raise click.UsageError("SQL statement cannot be empty.")
   
   if lang == SupportedLanguages.CSHARP:
       click.echo("Generate CSharp Model")

if __name__ == "__main__":
    main()       

  