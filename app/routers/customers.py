import time
import uuid
from fastapi import APIRouter, HTTPException, Path
from app.schemas import CustomerCreate, CustomerResponse, CustomerListResponse, RFCErrorResponse
from app.database import CUSTOMERS

router = APIRouter(prefix="/v1/customers", tags=["Customers"])

@router.get(
    "",
    response_model=CustomerListResponse,
    summary="Daftar Seluruh Pelanggan",
    description="Mengambil seluruh data profil pelanggan yang terdaftar pada sistem toko roti."
)
def list_customers():
    return {
        "object": "list",
        "url": "/v1/customers",
        "has_more": False,
        "data": list(CUSTOMERS.values())
    }

@router.post(
    "",
    response_model=CustomerResponse,
    status_code=201,
    summary="Mendaftarkan Pelanggan Baru",
    description="Membuat data profil pelanggan baru ke dalam sistem.",
    responses={
        400: {"model": RFCErrorResponse, "description": "Parameter permintaan tidak valid"}
    }
)
def create_customer(payload: CustomerCreate):
    cus_id = f"cus_{uuid.uuid4().hex[:8]}"
    customer_data = {
        "id": cus_id,
        "object": "customer",
        "name": payload.name,
        "phone": payload.phone,
        "email": payload.email,
        "created": int(time.time())
    }
    CUSTOMERS[cus_id] = customer_data
    return customer_data

@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Detail Pelanggan",
    description="Mengambil data profil pelanggan berdasarkan ID pelanggan.",
    responses={
        404: {"model": RFCErrorResponse, "description": "Pelanggan tidak ditemukan"}
    }
)
def get_customer(customer_id: str = Path(..., examples=["cus_budi01"], description="ID unik pelanggan")):
    if customer_id not in CUSTOMERS:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "resource_missing",
                    "message": f"Customer dengan ID '{customer_id}' tidak ditemukan.",
                    "param": "customer_id"
                }
            }
        )
    return CUSTOMERS[customer_id]
