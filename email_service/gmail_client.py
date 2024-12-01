# email_service/gmail_client.py
from googleapiclient.discovery import build

def create_gmail_client(creds):
    return build('gmail', 'v1', credentials=creds)
