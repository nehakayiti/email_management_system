# email/email_service.py
from db.database import Database
from email_service.gmail_client import create_gmail_client
from datetime import datetime, timedelta
from collections import defaultdict
import re
import json
import base64
import quopri
from email import message_from_bytes
import logging
from config import EMAIL_BODY_TRUNCATION_LENGTH, TRUNCATION_INDICATOR, KEYWORDS_PATH, MAX_FETCH_EMAILS

class EmailService:
    def __init__(self, creds):
        self.service = create_gmail_client(creds)
        self.db = Database()
        try:
            with open(KEYWORDS_PATH, 'r') as f:
                self.keywords = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Keywords file not found at {KEYWORDS_PATH}. Using empty keywords.")
            self.keywords = {}

    def fetch_emails(self, date=None, max_results=MAX_FETCH_EMAILS):
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
                email_data = self.parse_email(msg)
                categorization = self.categorize_email(email_data)
                email_data.update({
                    'category': categorization['primary_category'],
                    'secondary_categories': ','.join(categorization['secondary_categories']),
                    'confidence_score': categorization['confidence'],
                    'all_categories': json.dumps(categorization['all_categories']),
                    'is_read': 'UNREAD' not in msg['labelIds'],
                    'is_important': 'IMPORTANT' in msg['labelIds'],
                    'user_feedback': None,  # To be filled by user feedback later
                    'user_tags': None,  # Add this line to include user_tags
                    'is_manual': 0,  # Default value
                    'manually_updated_category': None,  # Default value
                    'reviewed': 0,  # Default value
                    'ml_category': None  # Default value
                })
                print(f"Storing email: {email_data['subject']} (ID: {email_data['id']})")
                self.store_email(email_data, conn)
                emails.append(email_data)
        finally:
            conn.close()

        return emails


    def store_email(self, email, conn):
        """Store email in the database."""
        c = conn.cursor()

        # Insert email into the emails table
        c.execute('''INSERT OR REPLACE INTO emails 
                 (id, subject, snippet, date, label_ids, sender_email, email_body, 
                  attachment_info, received_time, category, user_tags, is_manual, 
                  manually_updated_category, reviewed, ml_category, confidence_score, 
                  is_read, is_important, user_feedback, secondary_categories, all_categories) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (email['id'], email['subject'], email['snippet'], email['date'], 
               email['label_ids'], email['sender_email'], email['email_body'], 
               email['attachment_info'], email['received_time'], email['category'],
               email['user_tags'], email['is_manual'], email['manually_updated_category'],
               email['reviewed'], email['ml_category'], email['confidence_score'],
               email['is_read'], email['is_important'], email['user_feedback'], 
               email['secondary_categories'], email['all_categories']))

        conn.commit()

    def parse_email(self, msg):
        """Parse the email message and extract relevant information."""
        headers = msg['payload']['headers']
        subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), '')
        sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), '')
        date = next((header['value'] for header in headers if header['name'].lower() == 'date'), '')

        # Extract the email body
        body = self.get_email_body(msg['payload'])
        
        if body:
            body = body[:EMAIL_BODY_TRUNCATION_LENGTH]
            if len(body) == EMAIL_BODY_TRUNCATION_LENGTH:
                body += TRUNCATION_INDICATOR
        
        if not body:
            logging.warning(f"Empty body for email with subject: {subject}")

        return {
            'id': msg['id'],
            'subject': subject,
            'snippet': msg['snippet'],
            'date': date,
            'label_ids': ','.join(msg['labelIds']),
            'sender_email': sender,
            'email_body': body,
            'attachment_info': json.dumps(self.get_attachment_info(msg)),
            'received_time': msg['internalDate']
        }

    def get_email_body(self, payload):
        """Recursively extract the email body from the payload."""
        if 'body' in payload and 'data' in payload['body']:
            return self.decode_body(payload['body']['data'])
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] in ['text/plain', 'text/html']:
                    return self.decode_body(part['body'].get('data', ''))
                elif 'parts' in part:
                    body = self.get_email_body(part)
                    if body:
                        return body
        
        logging.warning(f"Could not find body in payload: {payload}")
        return ''

    def decode_body(self, data):
        """Decode the email body from base64."""
        if not data:
            logging.warning("Empty body data")
            return ''
        try:
            decoded_bytes = base64.urlsafe_b64decode(data)
            email_msg = message_from_bytes(decoded_bytes)
            
            if email_msg.is_multipart():
                for part in email_msg.walk():
                    if part.get_content_type() in ['text/plain', 'text/html']:
                        return part.get_payload(decode=True).decode('utf-8', errors='replace')
            else:
                return email_msg.get_payload(decode=True).decode('utf-8', errors='replace')
        except Exception as e:
            logging.error(f"Error decoding email body: {e}")
            return ''

    def get_attachment_info(self, msg):
        """Extract attachment information from the email message."""
        attachments = []
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if 'filename' in part and part['filename']:
                    attachments.append({
                        'filename': part['filename'],
                        'mimeType': part['mimeType'],
                        'size': part['body'].get('size', 0)
                    })
        return attachments

    def categorize_email(self, email):
        """Categorize an email based on its content, labels, and other attributes."""
        
        categories = defaultdict(float)
        
        subject = email.get('subject', '').lower()
        sender = email.get('sender_email', '').lower()
        body = email.get('email_body', '').lower()
        labels = set(email.get('label_ids', '').split(','))
        is_read = email.get('is_read', False)
        is_important = email.get('is_important', False)
        
        # Check each category
        for category, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword.lower() in subject or keyword.lower() in body or keyword.lower() in sender:
                    categories[category] += 1
        
        # Additional logic for specific labels
        if 'CATEGORY_PERSONAL' in labels:
            categories['Personal'] += 1
        if 'CATEGORY_SOCIAL' in labels:
            categories['Social'] += 1
        if 'CATEGORY_PROMOTIONS' in labels:
            categories['Promotions'] += 1
        if 'CATEGORY_UPDATES' in labels:
            categories['Updates'] += 1
        if 'CATEGORY_FORUMS' in labels:
            categories['Forums'] += 1
        
        # Logic for unread and important emails
        if not is_read:
            categories['Important (Non-urgent)'] += 0.5
        if is_important:
            categories['Important (Non-urgent)'] += 1
        
        # Determine primary and secondary categories
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        primary_category = sorted_categories[0][0]
        secondary_categories = [cat for cat, score in sorted_categories[1:3] if score > 0]
        
        # Calculate confidence score
        total_score = sum(categories.values())
        confidence = categories[primary_category] / total_score if total_score > 0 else 0
        
        return {
            'primary_category': primary_category,
            'secondary_categories': secondary_categories,
            'confidence': confidence,
            'all_categories': dict(categories)
        }