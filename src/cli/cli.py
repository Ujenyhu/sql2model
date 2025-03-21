import os
import click
#import debugpy
from utils.var_helper import SupportedLanguages
from utils.validate_requets import validate_sql
from utils.app_helper import generate_doc
from parsers.csharp_parser import CSharpParser



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
        file_extension = ".cs"
  
   output = parser.convert_to_model()
   click.echo(output)

   #Write to file if sql file was provided
   if sql_file:
        output_filename = os.path.basename(sql_file).split(".")[0] + file_extension
        output_file = os.path.join(os.path.dirname(sql_file), output_filename)
        with open(output_file, "w") as model_file:
            model_file.write(generate_doc(lang))
            model_file.write(output)

        click.echo(f"Model saved to {output_file}")       

     

if __name__ == "__main__":
    cli()       

  