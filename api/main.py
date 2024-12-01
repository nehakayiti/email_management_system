from fastapi import FastAPI
from api.routers import auth

app = FastAPI()

# Include the auth router
app.include_router(auth.router, prefix="/auth", tags=["auth"])

@app.get("/")
async def root():
    return {"message": "Welcome to Taskeroo API"}


# Add any additional configuration or middleware here if needed

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
