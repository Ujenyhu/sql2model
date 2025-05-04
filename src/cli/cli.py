
import os
import sys
import re
import logging

import click

from utils.var_helper import SupportedLanguages
from utils.app_helper import generate_doc
from parsers.csharp_parser import CSharpParser


class FileError(click.ClickException):
    """File I/O errors (exit code 2)"""
    exit_code = 2


class ValidationError(click.ClickException):
    """SQL validation errors (exit code 3)"""
    exit_code = 3


class ParseError(click.ClickException):
    """Parser/runtime errors (exit code 4)"""
    exit_code = 4


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Basic SQL DDL validation:
      - Must contain a CREATE TABLE clause
      - Parentheses must be balanced
      - At least one bracketed column definition
    Returns (is_valid, error_message)
    """
    if not re.search(r"CREATE\s+TABLE", sql, re.IGNORECASE):
        return False, "Missing 'CREATE TABLE' statement."

    open_paren = sql.count('(')
    close_paren = sql.count(')')
    if open_paren != close_paren:
        return False, f"Unbalanced parentheses: found {open_paren} '(' vs {close_paren} ')'."

    if not re.search(r"\[\w+\]\s+\[\w+\]", sql):
        return False, "No valid bracketed column definitions (e.g. [ColName] [int])."

    return True, ""


@click.command()
@click.argument(
    "sql_files",
    nargs=-1,
    type=click.Path(exists=True, readable=True, dir_okay=False),
)
@click.option(
    "--sql", "-s",
    type=str,
    help="Raw SQL statement to convert to a model"
)
@click.option(
    "--lang", "-l",
    type=click.Choice([SupportedLanguages.CSHARP, "python"]),
    required=True,
    help="Target language for the generated model"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Enable verbose/debug output"
)
@click.option(
    "--fail-fast/--no-fail-fast",
    default=False,
    help="Stop on first error if set (default is to continue processing all inputs)."
)
def cli(sql_files, sql, lang, verbose, fail_fast):
    # Configure logging
    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        level=logging.DEBUG if verbose else logging.INFO
    )
    logger = logging.getLogger(__name__)
    if verbose:
        logger.debug("Verbose logging enabled")

    # Ensure some form of input
    if not sql_files and not sql and sys.stdin.isatty():
        raise click.UsageError(
            "Provide SQL via files, --sql, or pipe via stdin."
        )

    # Gather inputs: list of tuples (name, sql_text)
    inputs = []

    # File inputs
    if sql_files:
        for path in sql_files:
            abs_path = os.path.abspath(path)
            inputs.append((abs_path, None))

    # Inline SQL
    elif sql:
        inputs.append(("inline", sql))

    # Piped stdin
    else:
        inputs.append(("stdin", sys.stdin.read()))

    failures = []

    for name, sql_text in inputs:
        try:
            # Read file content if necessary
            if sql_text is None:
                logger.debug(f"Reading SQL from file: {name}")
                try:
                    with open(name, "r", encoding="utf-8") as f:
                        sql_text = f.read()
                except OSError as e:
                    raise FileError(f"Error reading SQL file '{name}': {e}")

            # Empty check
            if not sql_text or not sql_text.strip():
                raise ValidationError(f"SQL statement for '{name}' cannot be empty.")

            # SQL validation
            is_valid, err_msg = validate_sql(sql_text)
            if not is_valid:
                raise ValidationError(f"Invalid SQL in '{name}': {err_msg}")

            # Initialize parser
            if lang == SupportedLanguages.CSHARP:
                parser = CSharpParser(sql_text)
                ext = ".cs"
            elif lang == "python":
                raise ValidationError("Python parser is not implemented yet.")
            else:
                raise ValidationError(f"Unsupported language: {lang}")

            # Convert to model
            output = parser.convert_to_model()

            # Output to console
            click.echo(f"--- Model for '{name}' ---")
            click.echo(output)

            # Write to file if input was a file
            if name not in ("inline", "stdin"):
                base = os.path.basename(name)
                out_name = os.path.splitext(base)[0] + ext
                out_path = os.path.join(os.path.dirname(name), out_name)
                logger.debug(f"Writing output model to: {out_path}")
                try:
                    with open(out_path, "w", encoding="utf-8") as outf:
                        outf.write(generate_doc(lang))
                        outf.write(output)
                except OSError as e:
                    raise FileError(f"Error writing model file '{out_path}': {e}")
                click.echo(f"{name} -> Model saved to {out_path}")
            else:
                click.echo(f"{name} -> Model generated successfully.")

        except click.ClickException as e:
            click.echo(f"{name} -> {e.format_message()}", err=True)
            failures.append(e)
            if fail_fast:
                # Stop immediately on first error
                sys.exit(e.exit_code)

    # After processing all inputs
    if failures:
        click.echo(f"Finished with {len(failures)} error(s).", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()


