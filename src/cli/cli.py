import os
import click
from utils.var_helper import SupportedLanguages
from utils.validate_requets import validate_sql
from parsers.csharp_parser import CSharpParser
import debugpy


@click.command()
@click.argument("sql_file", required=False, type=click.Path(exists=True, readable=True, dir_okay=False))
@click.option("--sql", "-sql", type=str, help="SQL statement to convert to model")
@click.option("--lang", "-l", type=click.Choice(["python", "csharp"]), required=True, help="Programming language you want a model for")

def cli(sql_file, sql, lang):
   if not sql_file and not sql:
        raise click.UsageError("You must provide either an SQL file or an SQL statement.")
   
   sql_statement = sql

   #Read from file if provided
   if sql_file:
        sql_file = os.path.abspath(sql_file)
        with open(sql_file, "r") as file:
            sql_statement = file.read()



   if not sql_statement:
        raise click.UsageError("SQL statement cannot be empty.")
   

   if not validate_sql(sql_statement):
          raise click.UsageError("Invalid SQL! Please provide a valid CREATE TABLE statement.")
     

   if lang == SupportedLanguages.CSHARP:
        parser = CSharpParser(sql_statement)
  
   output = parser.convert_to_model()
   click.echo(output)

if __name__ == "__main__":
    cli()       

  