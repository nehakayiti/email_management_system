# db/test_database.py
import sqlite3
import pytest
from db.database import Database

@pytest.fixture
def db(tmpdir):
    db_path = tmpdir.join("test_taskeroo.db")
    return Database(db_path)

def test_create_tables(db):
    db.create_tables()
    
    conn = sqlite3.connect(db.db_path)
    c = conn.cursor()

    # Check if the emails table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emails'")
    assert c.fetchone() is not None

    # Check if the interactions table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='interactions'")
    assert c.fetchone() is not None

    conn.close()
