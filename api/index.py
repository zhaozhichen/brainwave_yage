import os
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Brainwave API is running", "status": "healthy"}

@app.get("/test")
async def test():
    return {"message": "Test endpoint working"}

# Standard Vercel Python handler
from mangum import Adapter
handler = Adapter(app) 