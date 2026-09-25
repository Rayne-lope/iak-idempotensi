import time
import uuid
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header, Query, Path, Response
from fastapi.responses import JSONResponse
from app.schemas import (
    OrderCreate,
    OrderResponse,
    OrderListResponse,
    RFCErrorResponse
)
from app.database import ORDERS, CUSTOMERS, PRODUCTS
from app.idempotency import check_idempotency, save_idempotency_record

router = APIRouter(prefix="/v1/orders", tags=["Orders"])

@router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
    summary="Membuat Pesanan [Idempoten - Pola Stripe]",
    description=(
        "**[Operasi Idempoten - Pola Stripe]**\n\n"
        "Membuat transaksi pesanan baru dan melakukan alokasi pengurangan stok produk secara otomatis.\n\n"
        "Endpoint ini mewajibkan/mendukung header `Idempotency-Key` (UUID v4) guna menjamin tidak terjadinya "
        "duplikasi order dan pengurangan stok berganda apabila terjadi pengulangan permintaan dari klien. "
        "Pengulangan permintaan dengan kunci sama dan payload sama akan mengembalikan respons *cache* (dengan header `Idempotent-Replay: true` dan `X-Cache-Lookup: HIT`). "
        "Jika kunci yang sama dipakai dengan payload berbeda, server mengembalikan status `HTTP 409 Conflict`."
    ),
    responses={
        201: {"model": OrderResponse, "description": "Pesanan berhasil dibuat"},
        400: {"model": RFCErrorResponse, "description": "Parameter tidak valid atau stok tidak mencukupi"},
        404: {"model": RFCErrorResponse, "description": "Pelanggan atau Produk tidak ditemukan"},
        409: {"model": RFCErrorResponse, "description": "Konflik Idempotency-Key digunakan dengan parameter berbeda"}
    }
)
def create_order(
    payload: OrderCreate,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key", description="Kunci unik (UUID v4) untuk mencegah duplikasi pemrosesan pesanan")
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

    # 2. Validasi Keberadaan Pelanggan
    if payload.customer_id not in CUSTOMERS:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "resource_missing",
                    "message": f"Customer '{payload.customer_id}' tidak ditemukan.",
                    "param": "customer_id"
                }
            }
        )

    # 3. Validasi Produk & Stok
    total_amount = 0
    order_items: List[dict] = []
    
    for item in payload.items:
        prod = PRODUCTS.get(item.product_id)
        if not prod:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "type": "invalid_request_error",
                        "code": "resource_missing",
                        "message": f"Produk roti '{item.product_id}' tidak ditemukan.",
                        "param": "items.product_id"
                    }
                }
            )
        if prod["stock"] < item.quantity:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "type": "invalid_request_error",
                        "code": "insufficient_stock",
                        "message": f"Stok untuk '{prod['name']}' tidak mencukupi (Tersedia: {prod['stock']}, Diminta: {item.quantity}).",
                        "param": "items.quantity"
                    }
                }
            )

    # 4. Alokasi Pengurangan Stok & Kalkulasi Total
    for item in payload.items:
        prod = PRODUCTS[item.product_id]
        prod["stock"] -= item.quantity
        subtotal = prod["unit_price"] * item.quantity
        total_amount += subtotal
        order_items.append({
            "product_id": prod["id"],
            "name": prod["name"],
            "unit_price": prod["unit_price"],
            "quantity": item.quantity,
            "subtotal": subtotal
        })

    # 5. Pembuatan Data Pesanan
    order_id = f"ord_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    order_data = {
        "id": order_id,
        "object": "order",
        "customer": payload.customer_id,
        "status": "pending_payment",
        "currency": "idr",
        "items": order_items,
        "total_amount": total_amount,
        "notes": payload.notes,
        "created": int(time.time())
    }

    ORDERS[order_id] = order_data

    # 6. Penyimpanan Rekaman Idempotensi
    if idempotency_key:
        save_idempotency_record(idempotency_key, payload_dict, 201, order_data)
        response.headers["Idempotent-Replay"] = "false"
        response.headers["X-Cache-Lookup"] = "MISS"

    return order_data

@router.get(
    "",
    response_model=OrderListResponse,
    summary="Daftar Pesanan",
    description="Mengambil daftar transaksi pesanan dengan dukungan navigasi kursor (cursor-based pagination) dan filter status."
)
def list_orders(
    limit: int = Query(10, ge=1, le=100, description="Jumlah data per halaman (1–100)", examples=[10]),
    starting_after: Optional[str] = Query(None, description="ID pesanan sebagai kursor untuk mengambil data setelah entri ini", examples=["ord_20260925_001"]),
    ending_before: Optional[str] = Query(None, description="ID pesanan sebagai kursor untuk mengambil data sebelum entri ini"),
    status: Optional[str] = Query(None, description="Filter berdasarkan status pesanan (misal: pending_payment, paid, completed)")
):
    all_orders = list(ORDERS.values())
    all_orders.sort(key=lambda x: x["created"])

    if status:
        all_orders = [o for o in all_orders if o.get("status") == status]

    start_index = 0
    if starting_after:
        idx_match = [i for i, o in enumerate(all_orders) if o["id"] == starting_after]
        if idx_match:
            start_index = idx_match[0] + 1
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "type": "invalid_request_error",
                        "code": "cursor_not_found",
                        "message": f"Cursor 'starting_after' bernilai '{starting_after}' tidak valid.",
                        "param": "starting_after"
                    }
                }
            )

    selected_slice = all_orders[start_index : start_index + limit]
    has_more = (start_index + limit) < len(all_orders)

    return {
        "object": "list",
        "url": "/v1/orders",
        "has_more": has_more,
        "data": selected_slice
    }

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Detail Pesanan",
    description="Mengambil rincian data transaksi pesanan berdasarkan ID pesanan.",
    responses={
        404: {"model": RFCErrorResponse, "description": "Pesanan tidak ditemukan"}
    }
)
def get_order(order_id: str = Path(..., examples=["ord_20260925_001"], description="ID unik pesanan")):
    if order_id not in ORDERS:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "resource_missing",
                    "message": f"Pesanan dengan ID '{order_id}' tidak ditemukan.",
                    "param": "order_id"
                }
            }
        )
    return ORDERS[order_id]

@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    summary="Membatalkan Pesanan [Idempoten - State Transition]",
    description=(
        "**[Operasi Idempoten - State Transition & Idempotency-Key]**\n\n"
        "Membatalkan pesanan yang belum selesai serta mengembalikan alokasi kuota stok produk.\n"
        "Mendukung header `Idempotency-Key` dan transisi status aman sehingga pemanggilan berulang tidak akan "
        "mengembalikan stok roti lebih dari 1 kali."
    ),
    responses={
        200: {"model": OrderResponse, "description": "Pesanan berhasil dibatalkan"},
        400: {"model": RFCErrorResponse, "description": "Status pesanan tidak memenuhi syarat untuk dibatalkan"},
        404: {"model": RFCErrorResponse, "description": "Pesanan tidak ditemukan"},
        409: {"model": RFCErrorResponse, "description": "Konflik kunci idempotensi"}
    }
)
def cancel_order(
    response: Response,
    order_id: str = Path(..., examples=["ord_20260925_002"], description="ID unik pesanan yang akan dibatalkan"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key", description="Kunci unik UUID v4")
):
    if idempotency_key:
        cached = check_idempotency(idempotency_key, {"order_id": order_id, "action": "cancel"})
        if cached:
            cached_status, cached_body = cached
            return JSONResponse(
                status_code=cached_status,
                content=cached_body,
                headers={"Idempotent-Replay": "true", "X-Cache-Lookup": "HIT"}
            )

    if order_id not in ORDERS:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "resource_missing",
                    "message": f"Pesanan '{order_id}' tidak ditemukan.",
                    "param": "order_id"
                }
            }
        )

    order = ORDERS[order_id]
    if order["status"] in ["cancelled", "completed"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "invalid_state_transition",
                    "message": f"Pesanan tidak dapat dibatalkan karena berstatus '{order['status']}'.",
                    "param": "status"
                }
            }
        )

    # Pengembalian stok produk
    for item in order["items"]:
        prod_id = item["product_id"]
        if prod_id in PRODUCTS:
            PRODUCTS[prod_id]["stock"] += item["quantity"]

    order["status"] = "cancelled"

    if idempotency_key:
        save_idempotency_record(idempotency_key, {"order_id": order_id, "action": "cancel"}, 200, order)
        response.headers["Idempotent-Replay"] = "false"
        response.headers["X-Cache-Lookup"] = "MISS"

    return order
