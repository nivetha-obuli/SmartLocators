from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.routers import analyze, validate
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="AI-Assisted Smart Locator Generator",
    description="Automatically analyze web pages and generate reliable XPath/CSS locators for automation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS — allow frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers FIRST so they take precedence
app.include_router(analyze.router)
app.include_router(validate.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Smart Locator Generator"}


# Mount static frontend at root as fallback (must be last)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")