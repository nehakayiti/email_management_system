# db/database.py
import sqlite3

class Database:
    def __init__(self, db_path='taskeroo.db'):
        self.db_path = db_path
        self.create_tables()
        
    def connect(self):
        """Connect to the SQLite database."""
        print(f"Connecting to Database at {self.db_path}")
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        """Create tables for emails and interactions."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Create table for emails
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
                    user_tags TEXT
                    manually_updated_category TEXT,
                    is_manual INTEGER,
                    reviewed INTEGER DEFAULT 0)
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

        # Add manually_updated_category column if it doesn't exist
        c.execute("PRAGMA table_info(emails)")
        columns = [column[1] for column in c.fetchall()]
        if 'manually_updated_category' not in columns:
            c.execute("ALTER TABLE emails ADD COLUMN manually_updated_category TEXT")
        
        # Add is_manual column if it doesn't exist
        if 'is_manual' not in columns:
            c.execute("ALTER TABLE emails ADD COLUMN is_manual INTEGER")
        
        # Add reviewed column if it doesn't exist
        if 'reviewed' not in columns:
            c.execute("ALTER TABLE emails ADD COLUMN reviewed INTEGER DEFAULT 0")

        conn.commit()
        conn.close()