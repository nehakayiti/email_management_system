from fastapi.testclient import TestClient
from api.main import app
from unittest.mock import patch

client = TestClient(app)

def test_authenticate_success():
    with patch('auth.gmail_auth.GmailAuth.authenticate') as mock_authenticate:
        mock_authenticate.return_value = True
        response = client.post("/auth/authenticate")
        assert response.status_code == 200
        assert response.json() == {"status": "success", "message": "Authentication successful"}

def test_authenticate_failure():
    with patch('auth.gmail_auth.GmailAuth.authenticate') as mock_authenticate:
        mock_authenticate.side_effect = Exception("Authentication failed")
        response = client.post("/auth/authenticate")
        assert response.status_code == 400
        assert response.json() == {"detail": "Authentication failed"}