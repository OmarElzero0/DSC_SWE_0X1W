from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Payment API")


class PaymentMethod(str, Enum):
    card = "card"
    wallet = "wallet"
    bank_transfer = "bank_transfer"


class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    refunded = "refunded"


class PaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    customer_id: str = Field(min_length=1, max_length=100)
    payment_method: PaymentMethod
    description: str | None = Field(default=None, max_length=500)


class PaymentResponse(BaseModel):
    payment_id: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    created_at: datetime


# Temporary storage for the exercise.
# A real implementation should use a database.
payments = {}
idempotency_store = {}


SUPPORTED_CURRENCIES = {
    "EGP",
    "USD",
    "EUR",
}


@app.post(
    "/api/v1/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    request: PaymentRequest,
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None),
):
    # Authentication
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Authentication is required.",
            },
        )

    # Idempotency
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MISSING_IDEMPOTENCY_KEY",
                "message": "Idempotency-Key header is required.",
            },
        )

    if request.currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_CURRENCY",
                "message": "The specified currency is not supported.",
            },
        )

    # Return the previous result for duplicate requests
    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    payment_id = f"PAY_{uuid4().hex[:12]}"

    payment = PaymentResponse(
        payment_id=payment_id,
        status=PaymentStatus.pending,
        amount=request.amount,
        currency=request.currency,
        created_at=datetime.now(timezone.utc),
    )

    payments[payment_id] = {
        "payment": payment,
        "customer_id": request.customer_id,
        "payment_method": request.payment_method,
        "description": request.description,
    }

    idempotency_store[idempotency_key] = payment

    return payment
