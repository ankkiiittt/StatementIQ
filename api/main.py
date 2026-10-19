"""FastAPI application initialization and route registrations."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db.session import init_db
from api.routes import categories, chat, insights, statements, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="StatementIQ API",
    description="Backend API for StatementIQ bank statement analyzer",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(statements.router)
app.include_router(transactions.router)
app.include_router(insights.router)
app.include_router(categories.router)
app.include_router(chat.router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
