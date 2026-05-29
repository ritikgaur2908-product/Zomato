import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from data.models import UserPreferences
from app.orchestrator import RecommendationOrchestrator

app = FastAPI(title="TasteFinder Backend API")

# Enable CORS for Vercel/Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to your Vercel URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the orchestrator
try:
    orchestrator = RecommendationOrchestrator()
except Exception as e:
    print(f"Error initializing orchestrator: {e}")
    orchestrator = None

@app.post("/recommend")
def get_recommendations(prefs: UserPreferences):
    if orchestrator is None:
        raise HTTPException(
            status_code=500,
            detail="Recommendation engine could not be initialized due to database load failure."
        )
    try:
        response = orchestrator.recommend(prefs)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy", "orchestrator_loaded": orchestrator is not None}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.server:app", host="0.0.0.0", port=port, reload=False)
