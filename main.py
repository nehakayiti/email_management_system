# main.py
from auth.gmail_auth import GmailAuth
from db.database import Database


def main():
    gmail_auth = GmailAuth()
    creds = gmail_auth.authenticate()
    if creds:
        print("Authentication successful")
        
        # Verify the database tables
        db = Database()
        emails_table_exists, interactions_table_exists = db.verify_tables()

        if emails_table_exists and interactions_table_exists:
            print("Both emails and interactions tables exist.")
        else:
            print("Tables verification failed.")
        
    else:
        print("Authentication failed")
            

if __name__ == "__main__":
    main()
