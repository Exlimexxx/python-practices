"""Схемы платежей."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    booking_id: int = Field(gt=0)
    amount: float = Field(gt=0, le=1_000_000)
    method: PaymentMethod = PaymentMethod.CARD


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    amount: float
    method: PaymentMethod
    status: PaymentStatus
    created_at: datetime
