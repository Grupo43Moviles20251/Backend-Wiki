from fastapi import FastAPI
from routes import analytics

app = FastAPI(
    title="Mi Backend de Analytics",
    version="1.0.0"
)

app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Analytics Backend"}