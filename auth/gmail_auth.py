# taskeroo/gmail_auth.py
import os.path
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError


class GmailAuthError(Exception):
    """Custom exception class for Gmail authentication errors."""
    pass

class GmailAuth:
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    def load_credentials(self):
        """Load credentials from the token.pickle file if it exists."""
        try:
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    return pickle.load(token)
        except (IOError, pickle.UnpicklingError) as e:
            self.logger.error(f"Failed to load credentials: {e}")
            raise GmailAuthError(f"Failed to load credentials: {e}")
        return None    

    def save_credentials(self, creds):
        """Save credentials to the token.pickle file."""
        try:
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        except IOError as e:
            self.logger.error(f"Failed to save credentials: {e}")
            raise GmailAuthError(f"Failed to save credentials: {e}")
            
    def get_new_credentials(self):
        """Get new credentials by prompting the user to log in."""
        try:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
            creds = flow.run_local_server(port=0)
            return creds
        except Exception as e:
            self.logger.error(f"Failed to get new credentials: {e}")
            raise GmailAuthError(f"Failed to get new credentials: {e}")
    
    def authenticate(self):
        """Authenticates the user and returns the credentials."""
        try:
            creds = self.load_credentials()
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except RefreshError as e:
                        self.logger.warning(f"Token refresh failed: {e}")
                        creds = self.get_new_credentials()
                else:
                    creds = self.get_new_credentials()
                self.save_credentials(creds)
            return creds
        except GmailAuthError as e:
            self.logger.error(f"Authentication failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during authentication: {e}")
            raise GmailAuthError(f"Authentication failed due to an unexpected error: {e}")