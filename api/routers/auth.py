from fastapi import APIRouter, HTTPException
from auth.gmail_auth import GmailAuth

router = APIRouter()

@router.post("/authenticate")
async def authenticate():
    gmail_auth = GmailAuth()
    try:
        creds = gmail_auth.authenticate()
        return {"status": "success", "message": "Authentication successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

