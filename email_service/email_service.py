# email/email_service.py
from db.database import Database
from email_service.gmail_client import create_gmail_client
from datetime import datetime, timedelta


class EmailService:
    def __init__(self, creds, db_path='taskeroo.db'):
        self.service = create_gmail_client(creds)
        self.db = Database(db_path)

    def fetch_emails(self, date=None, max_results=10):
        """Fetch emails for the specified date and store them in the database."""
        
        if not self.service:
            print('No Valid Credentials Provided')
            return []
            
        if date:
            start_date = datetime.strptime(date, '%Y-%m-%d')
            end_date = start_date + timedelta(days=1)
            query = f"after:{start_date.strftime('%Y/%m/%d')} before:{end_date.strftime('%Y/%m/%d')}"
        else:
            query = ''
                     
        # Fetch emails from Inbox
        results_inbox = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages_inbox = results_inbox.get('messages', [])
        print(f"Inbox: Fetched {len(messages_inbox)} messages.")

        # Fetch emails from Trash
        results_trash = self.service.users().messages().list(userId='me', q=query, labelIds=['TRASH'], maxResults=max_results).execute()
        messages_trash = results_trash.get('messages', [])
        print(f"Trash: Fetched {len(messages_trash)} messages.")

        messages = messages_inbox + messages_trash    
        
        if not messages:
            print('No messages found.')
            return []
        else:
            print(f'Fetched {len(messages)} messages.')
        
        emails = []
        
        # Open a single connection for all inserts
        conn = self.db.connect()
        try:
            for message in messages:
                msg = self.service.users().messages().get(userId='me', id=message['id']).execute()
                email = {
                    'id': msg['id'],
                    'subject': next(header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'),
                    'snippet': msg['snippet'],
                    'date': msg['internalDate'],
                    'label_ids': ','.join(msg['labelIds']),
                    'sender_email': next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'From'), 'Unknown'),
                    'email_body': msg.get('snippet', ''),
                    'attachment_info': 'Yes' if 'attachment' in msg else 'No',
                    'received_time': msg['internalDate']                    
                }
                category = self.categorize_email(email)
                email['category'] = category
                print(f"Storing email: {email['subject']} (ID: {email['id']})")
                self.store_email(email, conn)
                emails.append(email)
        finally:
            conn.close()

        return emails


    def store_email(self, email, conn):
        """Store email in the database."""
        c = conn.cursor()

        # Insert email into the emails table
        c.execute('''INSERT OR REPLACE INTO emails (id, subject, snippet, date, label_ids, sender_email, email_body, attachment_info, received_time, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (email['id'], email['subject'], email['snippet'], email['date'], email['label_ids'], email['sender_email'], email['email_body'], email['attachment_info'], email['received_time'], email['category']))

        conn.commit()

    def categorize_email(self, email):
        """Categorize an email based on its content and labels."""
    
        # Label-based categorization
        labels = email.get('label_ids', '').split(',')
    
        # If the email is promotional, unread, and in trash, mark it as unimportant
        if 'CATEGORY_PROMOTIONS' in labels and 'UNREAD' in labels and 'TRASH' in labels:
            return 'unimportant'
    
        # If the email is in trash and not unread, mark it as read and trash
        if 'TRASH' in labels and 'UNREAD' not in labels:
            return 'read_trash'
    
        # Keyword-based categorization for payment and invoice emails
        important_keywords = ['Payment', 'Invoice', 'Bill', 'Statement', 'Confirmation', 'Order', 'Receipt']
        if any(keyword.lower() in email['subject'].lower() for keyword in important_keywords):
            return 'important'
    
        # Sender-based categorization for summarizable emails
        known_senders = ['newsletter@', 'updates@', 'no-reply@', 'noreply@']
        if any(sender in email['sender_email'] for sender in known_senders):
            return 'summarizable'
    
        # Default to 'neutral' if no specific categorization applies
        return 'neutral'
