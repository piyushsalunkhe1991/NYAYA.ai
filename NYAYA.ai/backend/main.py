"""NYAYA.ai backend entry point.

Run from the backend folder:   uvicorn main:app --reload --port 8000
The same server also serves the frontend, so open http://127.0.0.1:8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import CORS_ORIGINS, FRONTEND_DIR
from database.db import init_db
from routes import auth, chat, dashboard, documents, history, legal


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create SQLite tables on first start
    yield


app = FastAPI(title="NYAYA.ai API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, chat.router, documents.router, legal.router, history.router, dashboard.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "NYAYA.ai"}


# API routes are registered first; everything else is the static frontend.
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
