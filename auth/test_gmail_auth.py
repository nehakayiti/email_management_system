# taskeroo/auth/test_gmail_auth.py
import os
import pytest
import pickle
from .gmail_auth import GmailAuth
from unittest.mock import patch, MagicMock
from google.auth.transport.requests import Request


@pytest.fixture
def gmail_auth():
    return GmailAuth()

def test_load_credentials(gmail_auth, tmpdir):
    # Set up a temporary token.pickle file
    creds = {"token": "test_token"}
    token_file = tmpdir.join("token.pickle")
    with open(token_file, 'wb') as f:
        pickle.dump(creds, f)

    # Change the path to the temporary directory
    original_path = os.getcwd()
    os.chdir(tmpdir)

    # Test load_credentials method
    loaded_creds = gmail_auth.load_credentials()
    assert loaded_creds == creds

    # Clean up
    os.chdir(original_path)

def test_save_credentials(gmail_auth, tmpdir):
    # Set up a temporary path for token.pickle file
    creds = {"token": "test_token"}
    token_file = tmpdir.join("token.pickle")

    # Change the path to the temporary directory
    original_path = os.getcwd()
    os.chdir(tmpdir)

    # Test save_credentials method
    gmail_auth.save_credentials(creds)
    with open(token_file, 'rb') as f:
        saved_creds = pickle.load(f)
    assert saved_creds == creds

    # Clean up
    os.chdir(original_path)
    

def test_get_new_credentials(gmail_auth):
    # Mock the InstalledAppFlow and the run_local_server method
    with patch('taskeroo.auth.gmail_auth.InstalledAppFlow.from_client_secrets_file') as mock_flow:
        # Create a mock flow instance and mock the return value of run_local_server
        mock_instance = MagicMock()
        mock_flow.return_value = mock_instance
        mock_instance.run_local_server.return_value = {"token": "test_token"}

        # Call the method
        creds = gmail_auth.get_new_credentials()

        # Verify the credentials and that run_local_server was called
        assert creds == {"token": "test_token"}
        mock_instance.run_local_server.assert_called_once_with(port=0)


def test_authenticate(gmail_auth):
    with patch.object(gmail_auth, 'load_credentials') as mock_load, \
         patch.object(gmail_auth, 'save_credentials') as mock_save, \
         patch.object(gmail_auth, 'get_new_credentials') as mock_get_new:

        # Case 1: Valid credentials loaded
        mock_valid_creds = MagicMock(valid=True)
        mock_load.return_value = mock_valid_creds
        creds = gmail_auth.authenticate()
        assert creds == mock_valid_creds
        mock_save.assert_not_called()
        mock_get_new.assert_not_called()

        # Case 2: Expired credentials with refresh token
        mock_expired_creds = MagicMock(valid=False, expired=True, refresh_token="refresh_token")
        mock_expired_creds.refresh = MagicMock()
        mock_load.return_value = mock_expired_creds

        creds = gmail_auth.authenticate()
        assert creds == mock_expired_creds
        mock_expired_creds.refresh.assert_called_once()
        mock_save.assert_called_once_with(mock_expired_creds)
        mock_get_new.assert_not_called()
        mock_save.reset_mock()

        # Case 3: No valid credentials
        mock_load.return_value = None
        mock_new_creds = MagicMock(valid=True)
        mock_get_new.return_value = mock_new_creds
        creds = gmail_auth.authenticate()
        assert creds == mock_new_creds
        mock_save.assert_called_once_with(mock_new_creds)
