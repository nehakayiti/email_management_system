# cli.py

import argparse
import os
import csv
from auth.gmail_auth import GmailAuth
from google.auth.transport.requests import Request
from email_service.email_service import EmailService
from db.database import Database


def main():
    parser = argparse.ArgumentParser(description="Taskeroo Command Line Interface")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Authentication commands
    auth_parser = subparsers.add_parser("auth", help="Authentication related commands")
    auth_parser.add_argument("action", choices=["login", "refresh", "reset"], help="Action to perform")
    
    # Email fetching commands
    fetch_parser = subparsers.add_parser("fetch", help="Fetch --date=YYYY-MM-DD 'fetches emails for the given date'")
    fetch_parser.add_argument("--date", type=str, help="Date to fetch emails (YYYY-MM-DD)")
    
    # Email categorization commands
    categorize_parser = subparsers.add_parser("categorize", help="categorize --date=YYYY-MM-DD 'categorizes emails for the given date'")
    categorize_parser.add_argument("--date", type=str, help="date to fetch and categorize emails for (YYYY-MM-DD)")
    
    # Feedback command
    feedback_parser = subparsers.add_parser('feedback', help='Provide feedback on email categorization')
    feedback_parser.add_argument('email_id', type=str, help='ID of the email to provide feedback on')
    feedback_parser.add_argument('category', type=str, help='Category to assign to the email')

    # Email deletion commands
    delete_parser = subparsers.add_parser("delete", help="Delete unimportant emails")
    
    # Database interaction commands
    db_parser = subparsers.add_parser("db", help="Database operations")
    db_parser.add_argument("action", choices=["create", "read", "update", "delete", "migrate_schema"], help="Action to perform")
    
    # Logging and summary commands
    log_parser = subparsers.add_parser("log", help="Log interactions")
    summary_parser = subparsers.add_parser("summary", help="Provide a summary of actions")
    
    #export parser
    export_parser = subparsers.add_parser("export", help="Export emails to CSV")
    
    args = parser.parse_args()
    
    if args.command == "auth":
        handle_auth(args.action)
    elif args.command == "fetch":
        handle_fetch(args.date)
    elif args.command == "categorize":
        handle_categorize(args.date)
    elif args.command == "feedback":
        handle_feedback(args.emaild_id, args.category)
    elif args.command == "delete":
        handle_delete()
    elif args.command == "db":
        handle_db(args.action)
    elif args.command == "log":
        handle_log()
    elif args.command == "summary":
        handle_summary()
    elif args.command == "export":
        export_emails_to_csv()
    else:
        parser.print_help()

def handle_auth(action):
    print(f"Handling auth action: {action}")
    gmail_auth = GmailAuth()
    
    if action == "login":
        creds = gmail_auth.authenticate()
        print("Authentication successful. Credentials saved.")
    elif action == "refresh":
        creds = gmail_auth.load_credentials()
        if creds:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    gmail_auth.save_credentials(creds)
                    print("Token refreshed successfully.")
                except RefreshError as e:
                    print(f"Failed to refresh token: {e}")
            elif creds.expired and not creds.refresh_token:
                print("Token is expired and no refresh token is available. Please log in again.")
            else:
                print("Token is still valid and does not need refresh.")
        else:
            print("No valid credentials found. Please log in first.")
    elif action == "reset":
        if os.path.exists('token.pickle'):
            os.remove('token.pickle')
            print("Token file removed. You will need to login again.")
        else:
            print("No token file found.")

def handle_fetch(date):
    print(f"Fetching emails for date: {date}")
    gmail_auth = GmailAuth()
    creds = gmail_auth.authenticate()
    
    email_service = EmailService(creds)
    
    if date is None:
        from datetime import datetime
        date = datetime.today().strftime('%Y-%m-%d')
    
    print(f"Fetching emails for date: {date}")
    email_service.fetch_emails(date=date)


def handle_categorize(date):
    print(f"Categorizing emails for date: {date}")
    creds = GmailAuth().authenticate()
    email_service = EmailService(creds)
    emails = email_service.fetch_emails(date=date)
    for email in emails:
        category = email_service.categorize_email(email)
        print(f"Email: {email['subject']}, labels: {email['label_ids']}, Category: {category}")
        
def handle_feedback(email_id, category):
    creds = GmailAuth().get_token()
    email_service = EmailService(creds)
    email_service.provide_feedback(email_id, category)
    
def handle_delete():
    print("Deleting unimportant emails")

def handle_db(action):
    print(f"Handling database action: {action}")
    if action=="migrate_schema":
        db = Database('taskeroo.db')
        db.migrate_schema()

def handle_log():
    print("Logging user interactions")

def handle_summary():
    print("Providing summary of actions")
    
    
def export_emails_to_csv():
    db = Database('taskeroo.db')
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM emails")
    rows = cursor.fetchall()
    
    with open('emails.csv', 'w', newline='') as csvfile:
        fieldnames = ['id', 'subject', 'snippet', 'date', 'label_ids', 'sender_email', 'email_body', 'attachment_info', 'received_time', 'category']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in rows:
            writer.writerow({
                'id': row[0],
                'subject': row[1],
                'snippet': row[2],
                'date': row[3],
                'label_ids': row[4],
                'sender_email': row[5],
                'email_body': row[6],
                'attachment_info': row[7],
                'received_time': row[8],
                'category': row[9]
            })
    
    print("Emails exported to emails.csv")


if __name__ == "__main__":
    main()
