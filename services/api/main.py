"""
LexBangla API entry point.

Start with:
    uvicorn main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.retrieval import router as retrieval_router

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title="LexBangla API",
    description="Semantic retrieval over Bangladeshi legal documents.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(retrieval_router)


@app.get("/health", tags=["meta"])
async def root_health() -> dict[str, str]:
    return {"status": "ok", "service": "lexbangla-api"}


def start() -> None:
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
    )


if __name__ == "__main__":
    start()
