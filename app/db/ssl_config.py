"""TLS configuration for the Postgres connection.

Why this exists: Azure Database for PostgreSQL Flexible Server ships with
``require_secure_transport = ON``, so the plain DSN this service builds locally
is refused outright by the server. Locally (docker-compose, ``postgres:16``)
there is no TLS listener at all, which is why ``disable`` is the default —
enabling TLS is a deploy-time decision, not a code one, and the same image has
to work in both places.

This service is synchronous and talks to Postgres through psycopg2 only (the
app and Alembic share one DSN), and psycopg2 understands libpq's ``sslmode``
natively as a query-string parameter — so the only translation needed is from
the env var to that suffix.

Modes mirror libpq's vocabulary so the env var reads the way a Postgres
operator expects:

``disable``      no TLS (local docker-compose)
``require``      encrypt, but do not validate the server certificate
``verify-full``  encrypt and validate certificate + hostname
"""

DISABLE = "disable"
REQUIRE = "require"
VERIFY_FULL = "verify-full"

_VALID_MODES = frozenset({DISABLE, REQUIRE, VERIFY_FULL})


def _validated(mode: str) -> str:
    normalized = (mode or DISABLE).strip().lower()
    if normalized not in _VALID_MODES:
        raise ValueError(f"Invalid DATABASE_SSL_MODE {mode!r}. Expected one of: {', '.join(sorted(_VALID_MODES))}")
    return normalized


def sslmode_query_suffix(mode: str) -> str:
    """Build the query-string suffix for a psycopg2 (sync) DSN.

    Empty string for ``disable``, so the DSN is byte-identical to what it was
    before TLS was configurable.
    """
    normalized = _validated(mode)
    if normalized == DISABLE:
        return ""
    return f"?sslmode={normalized}"
