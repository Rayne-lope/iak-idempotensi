from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Path
from app.schemas import ProductResponse, ProductListResponse, ProductStockUpdate, RFCErrorResponse
from app.database import PRODUCTS

router = APIRouter(prefix="/v1/products", tags=["Products"])

@router.get(
    "",
    response_model=ProductListResponse,
    summary="Daftar Produk",
    description="Mengambil daftar seluruh produk beserta informasi harga dan stok yang tersedia. Dapat difilter berdasarkan kategori produk."
)
def list_products(
    category: Optional[str] = Query(None, description="Filter berdasarkan kategori produk (misal: 'bread', 'pastry')", examples=["bread"])
):
    items = list(PRODUCTS.values())
    if category:
        items = [p for p in items if p.get("category") == category]
    
    return {
        "object": "list",
        "url": "/v1/products",
        "has_more": False,
        "data": items
    }

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Detail Produk",
    description="Mengambil rincian informasi produk berdasarkan ID produk.",
    responses={
        404: {"model": RFCErrorResponse, "description": "Produk tidak ditemukan"}
    }
)
def get_product(product_id: str = Path(..., examples=["prod_sourdough01"], description="ID unik produk")):
    if product_id not in PRODUCTS:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "resource_missing",
                    "message": f"Produk roti dengan ID '{product_id}' tidak ditemukan.",
                    "param": "product_id"
                }
            }
        )
    return PRODUCTS[product_id]

@router.put(
    "/{product_id}/stock",
    response_model=ProductResponse,
    summary="Perbarui Stok Produk [Idempoten - HTTP PUT]",
    description=(
        "Menetapkan nilai stok absolut untuk suatu produk roti. Operasi HTTP PUT ini bersifat **Idempoten** "
        "karena jika dipanggil berulang kali dengan nilai stok yang sama, nilai akhir stok pada sistem tetap sama."
    ),
    responses={
        404: {"model": RFCErrorResponse, "description": "Produk tidak ditemukan"}
    }
)
def update_product_stock(
    payload: ProductStockUpdate,
    product_id: str = Path(..., examples=["prod_sourdough01"], description="ID unik produk")
):
    if product_id not in PRODUCTS:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "type": "invalid_request_error",
                    "code": "resource_missing",
                    "message": f"Produk roti dengan ID '{product_id}' tidak ditemukan.",
                    "param": "product_id"
                }
            }
        )
    PRODUCTS[product_id]["stock"] = payload.stock
    return PRODUCTS[product_id]
