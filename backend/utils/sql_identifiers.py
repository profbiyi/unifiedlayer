"""
Safe SQL identifier quoting.

These helpers exist so table/column names that reach a raw SQL string (from a
destination's catalog, a user-authored quality check, or a generated model name)
are never interpolated unquoted. That prevents identifier injection into the
org's own warehouse and, just as importantly, makes identifiers that are SQL
reserved words or contain spaces/special characters work correctly.

ANSI double-quoting is used, which is correct for the analytics destinations we
run these against (PostgreSQL, Snowflake, Redshift, DuckDB). MySQL identifier
quoting (backticks) lives in ``api/routes/source_discovery._mysql_ident``.

Note: values (WHERE literals, LIMIT counts) must be passed as bound parameters,
not quoted with these helpers — quoting an identifier is not the same as
escaping a value.
"""
from __future__ import annotations


def quote_ident(name: str) -> str:
    """Double-quote a single SQL identifier, escaping embedded double quotes."""
    return '"' + str(name).replace('"', '""') + '"'


def quote_qualified(name: str) -> str:
    """Quote a possibly schema-qualified name.

    ``schema.table`` -> ``"schema"."table"``; a bare ``table`` -> ``"table"``.
    Splits on ``.`` so each part is quoted independently.
    """
    return ".".join(quote_ident(part) for part in str(name).split("."))
