from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from mangum import Adapter
import os

app = FastAPI(title="Brainwave API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Brainwave API is running", "status": "healthy"}

@app.get("/test")
async def test():
    return {"message": "Test endpoint working"}

@app.get("/health")
async def health():
    return {"status": "ok", "environment": "vercel"}

# Vercel handler
handler = Adapter(app) 