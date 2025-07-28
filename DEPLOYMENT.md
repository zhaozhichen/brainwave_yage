# Vercel Deployment Guide

## Overview

This guide explains how to deploy your Brainwave API to Vercel. Note that **WebSocket functionality will not work on Vercel** due to serverless limitations.

## What Works on Vercel

✅ **REST API Endpoints:**
- `/api/v1/readability` - Enhance text readability
- `/api/v1/ask_ai` - Ask AI questions  
- `/api/v1/correctness` - Check factual correctness

✅ **Static Files** (if needed)
✅ **Environment Variables**
✅ **FastAPI Features**

## What Doesn't Work on Vercel

❌ **WebSocket Connections** - Your real-time audio processing
❌ **Long-running Processes** - Audio streaming
❌ **File System Operations** - Audio file saving

## Deployment Steps

### 1. Install Vercel CLI
```bash
npm install -g vercel
```

### 2. Login to Vercel
```bash
vercel login
```

### 3. Set Environment Variables
In your Vercel dashboard or via CLI:
```bash
vercel env add OPENAI_API_KEY
```

### 4. Deploy
```bash
vercel --prod
```

## Alternative Deployment Options

### For Full Functionality (Including WebSockets):

1. **Railway** - Supports WebSockets and long-running processes
2. **Render** - Good for full-stack applications
3. **DigitalOcean App Platform** - Full server support
4. **Heroku** - Traditional hosting with WebSocket support

### Hybrid Approach:

1. Deploy REST API on Vercel
2. Deploy WebSocket server separately on Railway/Render
3. Connect frontend to both services

## Testing Your Deployment

After deployment, test your endpoints:

```bash
# Test readability endpoint
curl -X POST "https://your-app.vercel.app/api/v1/readability" \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a test text to improve readability."}'

# Test ask_ai endpoint  
curl -X POST "https://your-app.vercel.app/api/v1/ask_ai" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is machine learning?"}'

# Test correctness endpoint
curl -X POST "https://your-app.vercel.app/api/v1/correctness" \
  -H "Content-Type: application/json" \
  -d '{"text": "The Earth is flat."}'
```

## Environment Variables Required

- `OPENAI_API_KEY` - Your OpenAI API key

## Limitations

- **Function timeout**: 30 seconds max (configurable in vercel.json)
- **Memory limits**: 1024MB per function
- **No WebSocket support**: Use alternative platforms for real-time features
- **Cold starts**: First request may be slower

## Monitoring

- Use Vercel dashboard to monitor function execution
- Check logs for errors and performance
- Monitor API usage and costs 