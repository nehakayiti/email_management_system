# taskeroo/email_service/test_email_service.py

import pytest
from unittest.mock import patch, Mock
from email_service.email_service import EmailService
from db.database import Database
import re


@pytest.fixture
def mock_gmail_client():
    with patch('email_service.email_service.create_gmail_client') as mock:
        yield mock

@pytest.fixture
def mock_database():
    with patch('db.database.Database', autospec=True) as mock:
        yield mock

@pytest.fixture
def email_service(mock_gmail_client, mock_database):
    creds = {'token': 'test-token'}
    with patch('email_service.email_service.Database', mock_database):
        email_service_instance = EmailService(creds)
    return email_service_instance


def test_email_service_initialization(email_service, mock_gmail_client, mock_database):
    assert email_service.service == mock_gmail_client.return_value
    assert email_service.db == mock_database.return_value


def a_test_fetch_emails(email_service, mock_gmail_client, mock_database):
    # Sample data to be returned by the mocked methods for inbox and trash
    mock_gmail_client.return_value.users.return_value.messages.return_value.list.return_value.execute.side_effect = [
        {'messages': [{'id': '1'}, {'id': '2'}]},  # Inbox messages
        {'messages': [{'id': '3'}, {'id': '4'}]}   # Trash messages
    ]
    mock_gmail_client.return_value.users.return_value.messages.return_value.get.return_value.execute.side_effect = [
        {
            'id': '1',
            'snippet': 'Test Snippet 1',
            'internalDate': '123456789',
            'labelIds': ['INBOX'],
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject 1'},
                    {'name': 'From', 'value': 'test@example.com'}
                ]
            }
        },
        {
            'id': '2',
            'snippet': 'Test Snippet 2',
            'internalDate': '987654321',
            'labelIds': ['INBOX'],
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject 2'},
                    {'name': 'From', 'value': 'test2@example.com'}
                ]
            }
        },
        {
            'id': '3',
            'snippet': 'Test Snippet 3',
            'internalDate': '1122334455',
            'labelIds': ['TRASH'],
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject 3'},
                    {'name': 'From', 'value': 'test3@example.com'}
                ]
            }
        },
        {
            'id': '4',
            'snippet': 'Test Snippet 4',
            'internalDate': '5566778899',
            'labelIds': ['TRASH'],
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject 4'},
                    {'name': 'From', 'value': 'test4@example.com'}
                ]
            }
        }
    ]

    # Mock the store_email method to avoid database interaction
    mock_conn = Mock()
    mock_database.return_value.connect.return_value = mock_conn

    with patch.object(email_service, 'store_email') as mock_store_email:
        email_service.fetch_emails(date='2024-07-25')
        # Log the actual calls
        actual_calls = mock_store_email.call_args_list
        for call in actual_calls:
            print(f"Actual call: {call}")

        # Ensure store_email is called with the correct parameters
        expected_calls = [
            {
                'id': '1',
                'subject': 'Test Subject 1',
                'snippet': 'Test Snippet 1',
                'date': '123456789',
                'label_ids': 'INBOX',
                'sender_email': 'test@example.com',
                'email_body': 'Test Snippet 1',
                'attachment_info': 'No',
                'received_time': '123456789',
            },
            {
                'id': '2',
                'subject': 'Test Subject 2',
                'snippet': 'Test Snippet 2',
                'date': '987654321',
                'label_ids': 'INBOX',
                'sender_email': 'test2@example.com',
                'email_body': 'Test Snippet 2',
                'attachment_info': 'No',
                'received_time': '987654321',
            },
            {
                'id': '3',
                'subject': 'Test Subject 3',
                'snippet': 'Test Snippet 3',
                'date': '1122334455',
                'label_ids': 'TRASH',
                'sender_email': 'test3@example.com',
                'email_body': 'Test Snippet 3',
                'attachment_info': 'No',
                'received_time': '1122334455',
            },
            {
                'id': '4',
                'subject': 'Test Subject 4',
                'snippet': 'Test Snippet 4',
                'date': '5566778899',
                'label_ids': 'TRASH',
                'sender_email': 'test4@example.com',
                'email_body': 'Test Snippet 4',
                'attachment_info': 'No',
                'received_time': '5566778899',
            }
        ]
        for expected_call in expected_calls:
            mock_store_email.assert_any_call(expected_call, mock_conn)
        
        # Ensure store_email is called four times
        assert mock_store_email.call_count == 4


def test_store_email(email_service, mock_database):
    # Mock the database connection and cursor
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_database.return_value.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Sample email data
    email = {
        'id': '1',
        'subject': 'Test Subject',
        'snippet': 'Test Snippet',
        'date': '123456789',
        'label_ids': 'INBOX',
        'sender_email': 'test@example.com',
        'email_body': 'Test email body',
        'attachment_info': 'No',
        'received_time': '123456789',
        'category': 'neutral',
        'user_tags': None,
        'is_manual': False,
        'manually_updated_category': None,
        'reviewed': False,
        'ml_category': None,
        'confidence_score': None,
        'is_read': False,
        'is_important': False,
        'user_feedback': None,
        'secondary_categories': None,
        'all_categories': None
    }

    # Ensure the database connect method is called once before passing it to store_email
    with patch.object(email_service.db, 'connect', return_value=mock_conn) as mock_connect:
        # Call the store_email method
        email_service.store_email(email, mock_conn)
        
    # Ensure the cursor execute method is called with the correct SQL statement and parameters
    expected_sql = '''INSERT OR REPLACE INTO emails (id, subject, snippet, date, label_ids, sender_email, email_body, attachment_info, received_time, category, user_tags, is_manual, manually_updated_category, reviewed, ml_category, confidence_score, is_read, is_important, user_feedback, secondary_categories, all_categories) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
    
    # Normalize the SQL query strings by removing extra whitespace
    actual_sql = mock_cursor.execute.call_args[0][0]
    actual_sql = ''.join(actual_sql.split())
    expected_sql = ''.join(expected_sql.split())
    assert actual_sql == expected_sql, f"Expected SQL: {expected_sql}, but got: {actual_sql}"
        



def test_fetch_emails_no_messages(email_service, mock_gmail_client, mock_database):
    # Configure the mock to return no messages
    mock_gmail_client.return_value.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        'messages': []
    }

    # Mock the store_email method to avoid database interaction
    with patch.object(email_service, 'store_email') as mock_store_email:
        email_service.fetch_emails()
        # Ensure store_email is not called
        mock_store_email.assert_not_called()

