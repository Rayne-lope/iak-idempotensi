from typing import List, Optional
from pydantic import BaseModel, Field
import time

# --- Error Schemas (RFC 7807 / RFC 9457) ---

class ErrorBody(BaseModel):
    type: str = Field(..., examples=["invalid_request_error"])
    code: str = Field(..., examples=["idempotency_conflict"])
    message: str = Field(..., examples=["Keys for idempotent requests cannot be reused with different request body."])
    param: Optional[str] = Field(None, examples=["Idempotency-Key"])

class RFCErrorResponse(BaseModel):
    error: ErrorBody

# --- Customer Schemas ---

class CustomerCreate(BaseModel):
    name: str = Field(..., examples=["Budi Santoso"])
    phone: str = Field(..., examples=["081234567890"])
    email: Optional[str] = Field(None, examples=["budi@example.com"])

class CustomerResponse(BaseModel):
    id: str = Field(..., examples=["cus_9a8b1c"])
    object: str = Field("customer", examples=["customer"])
    name: str
    phone: str
    email: Optional[str]
    created: int = Field(default_factory=lambda: int(time.time()))

class CustomerListResponse(BaseModel):
    object: str = Field("list", examples=["list"])
    url: str = Field("/v1/customers", examples=["/v1/customers"])
    has_more: bool = Field(..., examples=[False])
    data: List[CustomerResponse]

# --- Product Schemas ---

class ProductResponse(BaseModel):
    id: str = Field(..., examples=["prod_sourdough01"])
    object: str = Field("product", examples=["product"])
    name: str = Field(..., examples=["Artisan Sourdough Country Loaf"])
    category: str = Field(..., examples=["bread"])
    unit_price: int = Field(..., examples=[45000], description="Harga dalam satuan IDR.")
    stock: int = Field(..., examples=[20], description="Jumlah ketersediaan stok.")
    description: Optional[str] = Field(None, examples=["Roti sourdough fermentasi 24 jam alami tanpa ragi instan."])

class ProductStockUpdate(BaseModel):
    stock: int = Field(..., ge=0, examples=[50], description="Jumlah stok absolut yang ditetapkan")

class ProductListResponse(BaseModel):
    object: str = Field("list", examples=["list"])
    url: str = Field("/v1/products", examples=["/v1/products"])
    has_more: bool = Field(..., examples=[False])
    data: List[ProductResponse]

# --- Order Item & Order Schemas ---

class OrderItemInput(BaseModel):
    product_id: str = Field(..., examples=["prod_sourdough01"])
    quantity: int = Field(..., gt=0, examples=[2])

class OrderItemDetail(BaseModel):
    product_id: str
    name: str
    unit_price: int
    quantity: int
    subtotal: int

class OrderCreate(BaseModel):
    customer_id: str = Field(..., examples=["cus_budi01"])
    items: List[OrderItemInput]
    notes: Optional[str] = Field(None, examples=["Potong slice tebal"])

class OrderResponse(BaseModel):
    id: str = Field(..., examples=["ord_20260925_001"])
    object: str = Field("order", examples=["order"])
    customer: str = Field(..., examples=["cus_budi01"])
    status: str = Field(..., examples=["pending_payment"], description="Status pesanan: pending_payment, paid, baking, ready_for_pickup, completed, cancelled.")
    currency: str = Field("idr", examples=["idr"])
    items: List[OrderItemDetail]
    total_amount: int = Field(..., examples=[90000])
    notes: Optional[str] = None
    created: int = Field(default_factory=lambda: int(time.time()))

class OrderListResponse(BaseModel):
    object: str = Field("list", examples=["list"])
    url: str = Field("/v1/orders", examples=["/v1/orders"])
    has_more: bool = Field(..., examples=[False])
    data: List[OrderResponse]

# --- Payment Schemas ---

class PaymentCreate(BaseModel):
    order_id: str = Field(..., examples=["ord_20260925_001"])
    amount: int = Field(..., gt=0, examples=[90000])
    payment_method: str = Field(..., examples=["qris"], description="Metode pembayaran: qris, va_bca, credit_card, cash.")

class PaymentResponse(BaseModel):
    id: str = Field(..., examples=["pay_trx_99a1b2"])
    object: str = Field("payment", examples=["payment"])
    order_id: str = Field(..., examples=["ord_20260925_001"])
    amount: int = Field(..., examples=[90000])
    currency: str = Field("idr", examples=["idr"])
    payment_method: str = Field(..., examples=["qris"])
    status: str = Field(..., examples=["settlement"], description="Status pembayaran: pending, settlement, denied, expired.")
    created: int = Field(default_factory=lambda: int(time.time()))
