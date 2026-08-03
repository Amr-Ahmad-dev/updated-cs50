import sqlite3

class DictionaryResult:
    """
    A wrapper that allows the result of cursor.fetchall() to be passed 
    directly into dict(), effectively converting the list of rows 
    into a dictionary keyed by their index (0, 1, 2...).
    """
    def __init__(self, rows):
        self.rows = [dict(row) for row in rows]

    def __iter__(self):
        # This makes dict(result) work by yielding (index, row_dict)
        for i, row in enumerate(self.rows):
            yield (i, row)

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
    conn = sqlite3.connect(
        f"C:\\Users\\amrrrr\\Downloads\\updated-cs50-main\\updated-cs50-main\\cs50-final\\databases\\{db_name}",
        factory=DictionaryConnection
    )
    conn.row_factory = sqlite3.Row
    return conn