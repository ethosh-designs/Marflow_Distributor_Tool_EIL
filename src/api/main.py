from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.resolver import ProductCodeResolver

app = FastAPI(title="Marflow Product Code Resolver", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_resolver: ProductCodeResolver | None = None


def get_resolver() -> ProductCodeResolver:
    global _resolver
    if _resolver is None:
        _resolver = ProductCodeResolver()
    return _resolver


class ResolveRequest(BaseModel):
    description: str


class ResolveResponse(BaseModel):
    input_description: str
    resolved_code: str
    method: str
    confidence: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/resolve", response_model=ResolveResponse)
def resolve(request: ResolveRequest) -> ResolveResponse:
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="Description cannot be empty")
    try:
        result = get_resolver().resolve(request.description.strip())
        return ResolveResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
