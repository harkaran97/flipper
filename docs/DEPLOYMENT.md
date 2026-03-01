# Flipper — Railway Deployment Guide

## Prerequisites
- Railway account (railway.app)
- GitHub repo connected to Railway

## Steps

### 1. Create Railway project
1. Go to railway.app → New Project
2. Select "Deploy from GitHub repo"
3. Select the flipper repository

### 2. Add PostgreSQL
1. In your Railway project → Add Service → Database → PostgreSQL
2. Railway automatically sets DATABASE_URL in your environment

### 3. Set environment variables
In Railway dashboard → your service → Variables, add:

| Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `EBAY_APP_ID` | Your eBay app ID |
| `EBAY_CERT_ID` | Your eBay cert ID |
| `LINKUP_API_KEY` | Your LinkUp API key |
| `EBAY_STUB` | `false` (for production) |
| `LINKUP_STUB` | `false` (for production) |
| `POLL_INTERVAL_SECONDS` | `180` |

Note: Do NOT set DATABASE_URL manually — Railway sets this automatically
from the PostgreSQL service.

### 4. Deploy
Railway deploys automatically on every push to main/master.
First deploy takes 3-5 minutes (Docker build).

### 5. Verify
Once deployed, visit:
`https://your-app.railway.app/health`

Expected response:
```json
{
  "status": "ok",
  "pipeline": {
    "ingestion": "running",
    "detection": "running",
    "estimation": "running",
    "valuation": "running",
    "scoring": "running"
  }
}
```

## Environment variable reference
See `backend/.env.example` for full list with descriptions.
