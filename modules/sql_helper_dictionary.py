import sqlite3
import os

class DictionaryResult:
    """
    A wrapper that allows the result of cursor.fetchall() to be passed 
    directly into dict(), effectively converting the list of rows 
    into a dictionary keyed by their index (0, 1, 2...).
    """
    def __init__(self, rows):
        self.rows = [dict(row) for row in rows]

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
        return dict(row) if row else None

    def fetchall(self):
        # Return our wrapper instead of a raw list
        return DictionaryResult(super().fetchall())

class DictionaryConnection(sqlite3.Connection):
    def cursor(self, *args, **kwargs):
        return super().cursor(factory=DictionaryCursor)

def get_db(db_name):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "databases", db_name)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(
        db_path,
        factory=DictionaryConnection
    )
    conn.row_factory = sqlite3.Row
    return conn