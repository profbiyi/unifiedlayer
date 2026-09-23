"""
Security regression: table/schema names in the discovery + preview endpoints
must never be string-interpolated raw into SQL. Postgres uses psycopg2's
sql.Identifier; MySQL uses the _mysql_ident backtick-quoter tested here.
"""
from backend.api.routes.source_discovery import _mysql_ident


def test_mysql_ident_backtick_quotes():
    assert _mysql_ident("users") == "`users`"


def test_mysql_ident_escapes_embedded_backtick():
    # A name trying to break out of the quotes is neutralised by doubling the tick.
    assert _mysql_ident("users`; DROP TABLE users; --") == "`users``; DROP TABLE users; --`"


def test_mysql_ident_handles_non_str():
    assert _mysql_ident(123) == "`123`"
