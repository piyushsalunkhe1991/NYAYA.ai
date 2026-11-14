"""SQLite access using only the standard library (no ORM needed)."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import DB_PATH
from models.tables import SCHEMA


def init_db() -> None:
    """Create the database file and tables if they do not exist."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def db():
    """Yield a connection; commit on success, roll back on error."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
