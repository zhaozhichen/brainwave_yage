import os
import logging
from fastapi import FastAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Brainwave API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Brainwave API is running", "status": "healthy"}

@app.get("/test")
async def test():
    return {"message": "Test endpoint working"}

# Vercel handler
handler = app 