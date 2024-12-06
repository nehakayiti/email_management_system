# db/database.py
import sqlite3
from config import DB_PATH

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.create_tables()
        
    def connect(self):
        """Connect to the SQLite database."""
        print(f"Connecting to Database at {self.db_path}")
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        """Create tables for emails and interactions."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Create table for emails with new fields
        c.execute('''CREATE TABLE IF NOT EXISTS emails
                    (id TEXT PRIMARY KEY,
                    subject TEXT,
                    snippet TEXT,
                    date TEXT,
                    label_ids TEXT,
                    sender_email TEXT,
                    email_body TEXT,
                    attachment_info TEXT,
                    received_time TEXT,
                    category TEXT,
                    secondary_categories TEXT,
                    confidence_score REAL,
                    all_categories TEXT,
                    ml_category TEXT,
                    is_read INTEGER,
                    is_important INTEGER,
                    user_feedback TEXT)
                ''')

        # Create table for interactions
        c.execute('''CREATE TABLE IF NOT EXISTS interactions
                     (email_id TEXT,
                      interaction TEXT,
                      timestamp TEXT,
                      FOREIGN KEY(email_id) REFERENCES emails(id))''')

        conn.commit()
        conn.close()
        
    def verify_tables(self):
        """Verify that the tables were created."""
        conn = self.connect()
        c = conn.cursor()

        # Check if the emails table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emails'")
        emails_table_exists = c.fetchone() is not None

        # Check if the interactions table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='interactions'")
        interactions_table_exists = c.fetchone() is not None

        conn.close()
        return emails_table_exists, interactions_table_exists

    def migrate_schema(self):
        """Migrate the database schema to add new columns."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Add new columns if they don't exist
        c.execute("PRAGMA table_info(emails)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'secondary_categories' not in columns:
            c.execute("ALTER TABLE emails ADD COLUMN secondary_categories TEXT")
        
        if 'all_categories' not in columns:
            c.execute("ALTER TABLE emails ADD COLUMN all_categories TEXT")

        conn.commit()
        conn.close()