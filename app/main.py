from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables early
load_dotenv()

from app.api import hubspot, integrations, issues, jira  # noqa: E402

app = FastAPI(title="KillTheNoise API")

# CORS setup
origins = [os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(hubspot.router)
app.include_router(issues.router)
app.include_router(integrations.router)
app.include_router(jira.router) 