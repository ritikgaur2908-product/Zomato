# TasteFinder Deployment Plan

This document outlines the step-by-step procedure to deploy the TasteFinder application to **Railway** and/or **Vercel**. 

Since the application uses a Next.js (Node.js) frontend that spawns a Python CLI script (`python -m app.main`) to compute recommendations, we have two deployment architectures:
1. **Option A: Unified Containerized Deployment on Railway (Recommended)**: Runs both Node.js and Python inside a single container on Railway. This is the simplest option as it does not require modifying the Next.js routes to call a remote API.
2. **Option B: Decoupled Deployment (Vercel + Railway)**: Deploys the Next.js frontend to Vercel and wraps the Python orchestrator in a lightweight FastAPI server deployed to Railway.

---

## Environment Variables Configuration Checklist

Make sure to configure the following environment variables in your deployment dashboard (Railway and/or Vercel):

| Variable Name | Description | Example / Recommended Value |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | LLM client to use | `groq` |
| `LLM_MODEL` | Model identifier | `llama-3.3-70b-versatile` |
| `LLM_API_KEY` | Your Groq API key | `gsk_...` |
| `DATASET_NAME` | Hugging Face Dataset path | `ManikaSaini/zomato-restaurant-recommendation` |
| `DATASET_CACHE_PATH` | Cache file path | `data/cache/restaurants.parquet` |
| `BUDGET_LOW_MAX` | Max price for low budget tier | `500` |
| `BUDGET_MEDIUM_MAX` | Max price for medium budget tier | `1500` |
| `NEXT_PUBLIC_BACKEND_API_URL` | URL of the Python API *(Only for Option B)* | `https://tastefinder-backend.up.railway.app` |

---

## Option A: Unified Containerized Deployment on Railway (Recommended)

This option deploys the entire repository as a single Docker container. Railway will build and host the container, making the Next.js app available publicly. Since the container contains both Node.js and Python 3, the Next.js backend routes can call `spawn("python", ...)` locally.

### 1. Create a `Dockerfile` in the root of the project
Create a file named `Dockerfile` at the root directory (`/Dockerfile`) with the following contents:

```dockerfile
# Use a multi-stage or combined build to get both Node and Python
FROM node:20-slim AS node-base
FROM python:3.11-slim

# Install Node.js from the node-base image
COPY --from=node-base /usr/local /usr/local

WORKDIR /app

# Install system dependencies needed for Python libraries (like pandas/numpy)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend packages and install
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm ci

# Copy the rest of the application
WORKDIR /app
COPY . .

# Build the Next.js frontend
WORKDIR /app/frontend
RUN npm run build

# Expose port and start Next.js
EXPOSE 3000
ENV PORT=3000
ENV NODE_ENV=production

# Start Next.js server
CMD ["npm", "start"]
```

### 2. Steps to Deploy on Railway
1. Sign in to your [Railway Dashboard](https://railway.app).
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select your TasteFinder repository.
4. Click **Variables** and add all the environment variables listed in the checklist above.
5. Railway will automatically detect the `Dockerfile` at the root, build it, and deploy it.
6. Once deployed, click **Settings** in Railway and click **Generate Domain** to get a public URL (e.g. `https://tastefinder-production.up.railway.app`).

---

## Option B: Decoupled Deployment (Next.js on Vercel + Python API on Railway)

Vercel is the premier platform for Next.js, but its serverless functions cannot run python files locally out of the box. If you want to deploy the frontend on Vercel, you should wrap the Python orchestrator into an API and host it on Railway.

### Step 1: Create a simple FastAPI server in the Python backend
Create a file named `app/server.py` in your repository:

```python
# app/server.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from data.models import UserPreferences, BudgetTier
from app.orchestrator import RecommendationOrchestrator
import uvicorn
import os

app = FastAPI(title="TasteFinder Backend API")

# Enable CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = RecommendationOrchestrator()

@app.post("/recommend")
def get_recommendations(prefs: UserPreferences):
    try:
        response = orchestrator.recommend(prefs)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

And add `fastapi` and `uvicorn` to your `requirements.txt`.

### Step 2: Deploy the FastAPI Backend to Railway
1. In Railway, click **New Project** -> **Deploy from GitHub repo**.
2. Set the build/start command under **Settings** -> **Start Command**:
   ```bash
   python -m uvicorn app.server:app --host 0.0.0.0 --port $PORT
   ```
3. Add the required environment variables (`LLM_API_KEY`, etc.) in the Railway dashboard.
4. Generate a public domain (e.g. `https://tastefinder-backend.up.railway.app`).

### Step 3: Deploy the Next.js Frontend to Vercel
1. Modify the frontend's API handler [route.ts](file:///c:/Users/Ritk%20Gaur/Desktop/Zomato/frontend/src/app/api/recommendations/route.ts) to forward requests to the Railway URL if running in production:

```typescript
// Replace the spawn("python", ...) logic with a direct fetch to Railway in production:
const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || "http://localhost:8000";

if (process.env.NODE_ENV === "production" || process.env.DEPLOY_DECOUPLED === "true") {
  const response = await fetch(`${backendUrl}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      location,
      budget,
      cuisine,
      min_rating,
      top_n,
      extras
    })
  });
  const data = await response.json();
  return NextResponse.json(data);
} else {
  // Use spawn local process for local dev env
}
```

2. Sign in to your [Vercel Dashboard](https://vercel.com).
3. Click **Add New** -> **Project** -> Import your repository.
4. Set the Root Directory parameter of Vercel to `frontend`.
5. Add the Environment Variable:
   - `NEXT_PUBLIC_BACKEND_API_URL` = `https://tastefinder-backend.up.railway.app`
6. Click **Deploy**. Vercel will build and host your Next.js app dynamically!
