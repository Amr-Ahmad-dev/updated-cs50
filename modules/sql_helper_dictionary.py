import os
import re
import logging
import sqlite3

logger = logging.getLogger("ledger.database")

# Safe wrapper for fetchall results that can be iterated or cast to dict/list
class DictionaryResult:
    def __init__(self, rows):
        self.rows = [dict(row) if not isinstance(row, dict) else row for row in rows]

    def __iter__(self):
        for row in self.rows:
            yield row

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        return self.rows[idx]

    def __bool__(self):
        return bool(self.rows)


class DictionaryCursor(sqlite3.Cursor):
    def fetchone(self):
        row = super().fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        rows = super().fetchall()
        return DictionaryResult(rows)


class DictionaryConnection(sqlite3.Connection):
    def cursor(self, *args, **kwargs):
        return super().cursor(factory=DictionaryCursor)


def _get_sqlite_db(db_name):
    """Returns a SQLite connection configured with WAL and dictionary rows."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "databases", db_name)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(
        db_path,
        factory=DictionaryConnection
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# PostgreSQL adapter classes for query compatibility
class PostgresCursorWrapper:
    def __init__(self, real_cursor):
        self._cursor = real_cursor

    def execute(self, query, params=None):
        # Convert SQLite '?' placeholders to PostgreSQL '%s'
        pg_query = query.replace("?", "%s")
        # Handle SQLite datetime('now') -> NOW()
        pg_query = re.sub(r"datetime\('now'\)", "NOW()", pg_query, flags=re.IGNORECASE)
        # Handle INSERT OR IGNORE -> ON CONFLICT DO NOTHING
        if re.search(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", pg_query, re.IGNORECASE):
            pg_query = re.sub(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", pg_query, flags=re.IGNORECASE)
            if "ON CONFLICT" not in pg_query.upper():
                pg_query = pg_query.rstrip(" ;") + " ON CONFLICT DO NOTHING"
        
        if params is None:
            return self._cursor.execute(pg_query)
        elif isinstance(params, (list, tuple)):
            return self._cursor.execute(pg_query, tuple(params))
        elif isinstance(params, dict):
            # Convert :name to %(name)s for psycopg2
            pg_query = re.sub(r":([a-zA-Z0-9_]+)", r"%(\1)s", pg_query)
            return self._cursor.execute(pg_query, params)
        else:
            return self._cursor.execute(pg_query, params)

    def executescript(self, script):
        for stmt in script.split(";"):
            stmt = stmt.strip()
            if stmt:
                self.execute(stmt)

    def fetchone(self):
        row = self._cursor.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        rows = self._cursor.fetchall()
        return DictionaryResult(rows)

    @property
    def lastrowid(self):
        return getattr(self._cursor, "lastrowid", None)

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()


class PostgresConnectionWrapper:
    def __init__(self, real_conn):
        self._conn = real_conn

    def cursor(self, *args, **kwargs):
        from psycopg2.extras import RealDictCursor
        kwargs["cursor_factory"] = RealDictCursor
        return PostgresCursorWrapper(self._conn.cursor(*args, **kwargs))

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def executescript(self, script):
        cur = self.cursor()
        cur.executescript(script)
        return cur

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._conn.rollback()
        else:
            self._conn.commit()


_ACTIVE_BACKEND = "sqlite"

def get_active_backend():
    return _ACTIVE_BACKEND

def get_db(db_name="main.db"):
    """
    Returns a database connection.
    Attempts PostgreSQL when configured via environment variables.
    Automatically and safely falls back to local SQLite if PostgreSQL
    is unconfigured, unavailable, or encounters connection failure.
    """
    global _ACTIVE_BACKEND
    pg_url = os.environ.get("DATABASE_URL")
    pg_host = os.environ.get("POSTGRES_HOST") or os.environ.get("PGHOST")
    
    if pg_url or pg_host:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            if pg_url:
                conn = psycopg2.connect(pg_url)
            else:
                conn = psycopg2.connect(
                    host=pg_host,
                    port=int(os.environ.get("POSTGRES_PORT") or os.environ.get("PGPORT", 5432)),
                    dbname=os.environ.get("POSTGRES_DB") or os.environ.get("PGDATABASE", "ledger"),
                    user=os.environ.get("POSTGRES_USER") or os.environ.get("PGUSER", "postgres"),
                    password=os.environ.get("POSTGRES_PASSWORD") or os.environ.get("PGPASSWORD", "")
                )
            _ACTIVE_BACKEND = "postgresql"
            return PostgresConnectionWrapper(conn)
        except Exception as e:
            # Mask sensitive parts of error message if any
            err_msg = str(e)
            target = pg_host or (pg_url.split("@")[-1] if pg_url and "@" in pg_url else "configured host")
            logger.warning(
                f"[Database Fallback] PostgreSQL connection to '{target}' failed: {err_msg}. "
                f"Falling back to local SQLite ({db_name})."
            )
            print(f"[Database] PostgreSQL connection failed: {err_msg}. Falling back to SQLite ({db_name}).")
            _ACTIVE_BACKEND = "sqlite"
            return _get_sqlite_db(db_name)
    else:
        _ACTIVE_BACKEND = "sqlite"
        return _get_sqlite_db(db_name)