"""Единая точка входа клиента в микросервисную систему."""
from __future__ import annotations
import os
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from app.resilience import CircuitBreaker, CircuitOpenError, retry_async

app = FastAPI(title="Hotel API Gateway", version="1.0.0")
BREAKERS = {name: CircuitBreaker(2, 3.0) for name in ("rooms", "guests", "bookings")}
BASES = {
    "rooms": os.getenv("ROOMS_SERVICE_URL", "http://rooms-service:8001"),
    "guests": os.getenv("GUESTS_SERVICE_URL", "http://guests-service:8002"),
    "bookings": os.getenv("BOOKINGS_SERVICE_URL", "http://bookings-service:8003"),
}


async def proxy(service: str, method: str, path: str, request: Request | None = None) -> Any:
    url = BASES[service] + path
    body = await request.json() if request is not None and method in {"POST", "PUT", "PATCH"} else None
    params = dict(request.query_params) if request is not None else None
    async def operation():
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.request(method, url, json=body, params=params)
            if response.status_code >= 400:
                response.raise_for_status()
            if response.status_code == 204:
                return Response(status_code=204)
            return JSONResponse(status_code=response.status_code, content=response.json())
    try:
        return await BREAKERS[service].call(lambda: retry_async(operation, attempts=2))
    except CircuitOpenError as exc:
        raise HTTPException(503, f"Сервис {service} временно недоступен (Circuit Breaker OPEN)") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(exc.response.status_code, exc.response.text) from exc
    except Exception as exc:
        raise HTTPException(503, f"Сервис {service} не ответил после повторных попыток") from exc


@app.get("/health")
async def health():
    return {"status": "healthy", "gateway": True}


@app.api_route("/api/rooms", methods=["GET", "POST"])
async def rooms_collection(request: Request):
    return await proxy("rooms", request.method, "/rooms", request)


@app.api_route("/api/rooms/{item_id}", methods=["GET", "PUT", "DELETE"])
async def room_item(item_id: int, request: Request):
    return await proxy("rooms", request.method, f"/rooms/{item_id}", request)


@app.api_route("/api/guests", methods=["GET", "POST"])
async def guests_collection(request: Request):
    return await proxy("guests", request.method, "/guests", request)


@app.api_route("/api/guests/{item_id}", methods=["GET", "PUT", "DELETE"])
async def guest_item(item_id: int, request: Request):
    return await proxy("guests", request.method, f"/guests/{item_id}", request)


@app.api_route("/api/bookings", methods=["GET", "POST"])
async def bookings_collection(request: Request):
    return await proxy("bookings", request.method, "/bookings", request)


@app.api_route("/api/bookings/{item_id}", methods=["GET", "DELETE"])
async def booking_item(item_id: int, request: Request):
    return await proxy("bookings", request.method, f"/bookings/{item_id}", request)
