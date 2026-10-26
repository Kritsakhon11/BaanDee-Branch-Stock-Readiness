from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

HERE = Path(__file__).resolve().parent


def _load(name: str) -> dict:
    return json.loads((HERE / "fixtures" / name).read_text(encoding="utf-8"))


ORDERS = _load("orders.json")
INVENTORY = _load("inventory.json")
TICKETS = _load("tickets.json")

app = FastAPI(title="BaanDee Simulated Company API", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "baandee-classroom-api"}


@app.get("/orders/{order_id}")
def get_order(order_id: str) -> dict:
    record = ORDERS.get(order_id.upper())
    if record is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return record


@app.get("/inventory/{product_id}")
def get_inventory(product_id: str) -> dict:
    record = INVENTORY.get(product_id.upper())
    if record is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return record


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict:
    record = TICKETS.get(ticket_id.upper())
    if record is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return record
