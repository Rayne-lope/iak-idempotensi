import time
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Path, Response
from fastapi.responses import JSONResponse
from app.schemas import (
    PaymentCreate,
    PaymentResponse,
    RFCErrorResponse
)
from app.database import PAYMENTS, ORDERS
from app.idempotency import check_idempotency, save_idempotency_record

router = APIRouter(prefix="/v1/payments", tags=["Payments"])

@router.post(
    "",
    response_model=PaymentResponse,
    status_code=201,
    summary="Memproses Pembayaran [Idempoten - Pola Stripe]",
    description=(
        "**[Operasi Idempoten - Pola Stripe Finansial]**\n\n"
        "Memproses transaksi pembayaran pesanan toko roti. Operasi ini dilindungi oleh header `Idempotency-Key` (UUID v4) "
        "guna menjamin bahwa pelanggan tidak akan terdebit dua kali (*double charging*) saat terjadi kegagalan/timeout jaringan. "
        "Pengulangan permintaan dengan kunci sama akan mengembalikan respons *cache* (dengan header `Idempotent-Replay: true` dan `X-Cache-Lookup: HIT`)."
    ),
    responses={
        201: {"model": PaymentResponse, "description": "Pembayaran berhasil diproses"},
        400: {"model": RFCErrorResponse, "description": "Nominal pembayaran tidak sesuai atau status pesanan tidak valid"},
        404: {"model": RFCErrorResponse, "description": "Pesanan tidak ditemukan"},
        409: {"model": RFCErrorResponse, "description": "Konflik kunci idempotensi"}
    }
)
def create_payment(
    payload: PaymentCreate,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key", description="Kunci unik UUID v4 untuk mencegah transaksi pembayaran ganda")
):
    payload_dict = payload.model_dump()

    # 1. Validasi Idempotensi
    if idempotency_key:
        cached = check_idempotency(idempotency_key, payload_dict)
        if cached:
            cached_status, cached_body = cached
            return JSONResponse(
                status_code=cached_status,
                content=cached_body,
                headers={"Idempotent-Replay": "true", "X-Cache-Lookup": "HIT"}
            )

    # 2. Validasi Keberadaan Pesanan
    if payload.order_id not in ORDERS:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "resource_missing",
                    "message": f"Pesanan '{payload.order_id}' tidak ditemukan.",
                    "param": "order_id"
                }
            }
        )

    order = ORDERS[payload.order_id]

    if order["status"] == "paid" or order["status"] == "completed":
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "order_already_paid",
                    "message": f"Pesanan '{payload.order_id}' sudah lunas.",
                    "param": "order_id"
                }
            }
        )

    if order["status"] == "cancelled":
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "order_cancelled",
                    "message": f"Pesanan '{payload.order_id}' telah dibatalkan, pembayaran ditolak.",
                    "param": "order_id"
                }
            }
        )

    # 3. Validasi Kesesuaian Nominal Pembayaran
    if payload.amount != order["total_amount"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "amount_mismatch",
                    "message": f"Jumlah bayar ({payload.amount}) tidak sesuai total tagihan pesanan ({order['total_amount']}).",
                    "param": "amount"
                }
            }
        )

    # 4. Pembuatan Data Pembayaran
    pay_id = f"pay_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    payment_data = {
        "id": pay_id,
        "object": "payment",
        "order_id": payload.order_id,
        "amount": payload.amount,
        "currency": "idr",
        "payment_method": payload.payment_method,
        "status": "settlement",
        "created": int(time.time())
    }

    PAYMENTS[pay_id] = payment_data
    order["status"] = "paid"

    # 5. Rekam Idempotensi
    if idempotency_key:
        save_idempotency_record(idempotency_key, payload_dict, 201, payment_data)
        response.headers["Idempotent-Replay"] = "false"
        response.headers["X-Cache-Lookup"] = "MISS"

    return payment_data

@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Detail Pembayaran",
    description="Mengambil informasi dan status transaksi pembayaran berdasarkan ID pembayaran.",
    responses={
        404: {"model": RFCErrorResponse, "description": "Pembayaran tidak ditemukan"}
    }
)
def get_payment(payment_id: str = Path(..., examples=["pay_trx_001"], description="ID unik pembayaran")):
    if payment_id not in PAYMENTS:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "resource_missing",
                    "message": f"Pembayaran dengan ID '{payment_id}' tidak ditemukan.",
                    "param": "payment_id"
                }
            }
        )
    return PAYMENTS[payment_id]

@router.post(
    "/{payment_id}/confirm",
    response_model=PaymentResponse,
    summary="Konfirmasi Pembayaran [Idempoten - State Transition]",
    description=(
        "**[Operasi Idempoten - State Transition]**\n\n"
        "Melakukan konfirmasi status penyelesaian transaksi pembayaran. Operasi ini idempoten karena "
        "menetapkan status akhir ke `settlement`. Pemanggilan berulang tidak mengubah hasil akhir."
    ),
    responses={
        200: {"model": PaymentResponse, "description": "Pembayaran dikonfirmasi"},
        404: {"model": RFCErrorResponse, "description": "Pembayaran tidak ditemukan"}
    }
)
def confirm_payment(
    response: Response,
    payment_id: str = Path(..., examples=["pay_trx_001"], description="ID unik pembayaran"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key", description="Kunci unik UUID v4")
):
    if idempotency_key:
        cached = check_idempotency(idempotency_key, {"payment_id": payment_id, "action": "confirm"})
        if cached:
            cached_status, cached_body = cached
            return JSONResponse(status_code=cached_status, content=cached_body, headers={"Idempotent-Replay": "true", "X-Cache-Lookup": "HIT"})

    if payment_id not in PAYMENTS:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "resource_missing",
                    "message": f"Pembayaran '{payment_id}' tidak ditemukan.",
                    "param": "payment_id"
                }
            }
        )

    pay = PAYMENTS[payment_id]
    pay["status"] = "settlement"

    if idempotency_key:
        save_idempotency_record(idempotency_key, {"payment_id": payment_id, "action": "confirm"}, 200, pay)
        response.headers["Idempotent-Replay"] = "false"
        response.headers["X-Cache-Lookup"] = "MISS"

    return pay
