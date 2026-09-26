"""Tests for safe SQL identifier quoting."""
from backend.utils.sql_identifiers import quote_ident, quote_qualified


def test_quote_ident_wraps_in_double_quotes():
    assert quote_ident("users") == '"users"'


def test_quote_ident_escapes_embedded_double_quotes():
    # a name carrying a double quote must have it doubled, not left to break out
    assert quote_ident('a"b') == '"a""b"'


def test_quote_ident_neutralizes_injection_attempt():
    # the classic identifier-injection payload becomes an inert (if silly) name
    out = quote_ident('x"; DROP TABLE users; --')
    assert out.startswith('"') and out.endswith('"')
    # the closing quote of the payload is escaped, so it cannot terminate early
    assert '""' in out


def test_quote_ident_handles_reserved_word_and_spaces():
    assert quote_ident("order") == '"order"'
    assert quote_ident("full name") == '"full name"'


def test_quote_qualified_splits_and_quotes_each_part():
    assert quote_qualified("public.orders") == '"public"."orders"'


def test_quote_qualified_bare_name():
    assert quote_qualified("orders") == '"orders"'
