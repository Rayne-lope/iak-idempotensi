from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import customers, products, orders, payments

app = FastAPI(
    title="Bakery Service API",
    description="""
Dokumentasi teknis RESTful API Bakery Service untuk operasional penjualan produk roti dan pastry, pengelolaan data pelanggan, transaksi pemesanan, serta pemrosesan pembayaran.

---

### Sumber Daya (Resources)
API ini menyediakan pengelolaan untuk 4 entitas utama:
1. **Customers (`/v1/customers`)**: Registrasi, detail, dan penelusuran seluruh data profil pelanggan.
2. **Products (`/v1/products`)**: Katalog produk roti, informasi harga satuan (IDR), pemantauan stok fisik, serta pembaruan stok absolut.
3. **Orders (`/v1/orders`)**: Pembuatan pesanan baru, alokasi pengurangan stok, pembatalan pesanan, dan penelusuran riwayat pesanan (cursor-based pagination).
4. **Payments (`/v1/payments`)**: Pemrosesan transaksi pembayaran dan verifikasi status penyelesaian transaksi (*settlement*).

---

### Daftar 4 Operasi Idempoten Utama dalam Sistem:
Berikut adalah 4 operasi mutasi yang secara eksplisit dilindungi dan bersifat **Idempoten** (*Idempotent Operations*):

1. **`POST /v1/orders` [Idempoten - Pola Stripe]**
   - **Peran:** Membuat pesanan baru dan mereservasi kuota stok fisik roti.
   - **Mekanisme:** Dilindungi oleh header `Idempotency-Key` (UUID v4). Pengulangan permintaan (*retry*) akibat kegagalan jaringan akan mengembalikan respons *cache* asli (`Idempotent-Replay: true`, `X-Cache-Lookup: HIT`) tanpa menduplikasi nomor pesanan atau memotong stok roti untuk kedua kalinya.
   - **Proteksi Konflik:** Jika kunci yang sama dikirim dengan isi *payload* pesanan berbeda, sistem mengembalikan status `HTTP 409 Conflict`.

2. **`POST /v1/orders/{order_id}/cancel` [Idempoten - State Transition & Idempotency-Key]**
   - **Peran:** Membatalkan pesanan yang belum selesai dan mengembalikan alokasi stok produk roti ke inventaris.
   - **Mekanisme:** Transisi status aman dan header `Idempotency-Key` memastikan bahwa pemanggilan berulang tidak akan menambah kuota stok roti berulang kali.

3. **`POST /v1/payments` [Idempoten - Pola Stripe Finansial]**
   - **Peran:** Mengeksekusi penagihan dana pembayaran pesanan toko roti.
   - **Mekanisme:** Dilindungi oleh header `Idempotency-Key` (UUID v4) guna mencegah risiko fatal pendebitan berganda (*double charging*) pada akun/e-wallet pelanggan saat *timeout* jaringan terjadi.

4. **`POST /v1/payments/{payment_id}/confirm` [Idempoten - State Transition]**
   - **Peran:** Konfirmasi penyelesaian transaksi pembayaran menjadi status `settlement`.
   - **Mekanisme:** Menetapkan nilai status akhir secara deterministik, sehingga pemanggilan berulang kali tidak mengubah efek samping pada sistem.

*(Catatan Tambahan: Operasi `PUT /v1/products/{product_id}/stock` juga merupakan operasi idempoten standar HTTP untuk penetapan stok absolut, serta seluruh pemanggilan metode `GET` bersifat aman dan idempoten).*

---

### Spesifikasi Teknis Tambahan:
- **Navigasi Kursor (*Cursor-Based Pagination*)**: Endpoint `GET /v1/orders` menggunakan parameter `limit`, `starting_after`, dan `ending_before` dengan struktur *envelope* resmi (`object`, `url`, `has_more`, `data`).
- **Format Kesalahan**: Struktur respons kesalahan mengacu pada standar RFC 7807 / RFC 9457 (*Problem Details for HTTP APIs*).
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Format Error Validasi Permintaan (RFC 7807)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_err = errors[0] if errors else {}
    loc = ".".join(str(x) for x in first_err.get("loc", []) if x not in ("body", "query", "header", "path"))
    msg = first_err.get("msg", "Parameter permintaan tidak valid.")
    err_type = first_err.get("type", "invalid_request_error")

    code = "parameter_missing" if "missing" in err_type else "parameter_invalid"

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "type": "invalid_request_error",
                "code": code,
                "message": msg,
                "param": loc or None
            }
        }
    )

# Format Error HTTP Umum (RFC 7807)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "api_error",
                "code": f"http_{exc.status_code}",
                "message": str(exc.detail),
                "param": None
            }
        }
    )

# Pendaftaran Router
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)

@app.get("/", include_in_schema=False)
def root():
    """Mengalihkan rute root langsung ke Swagger UI."""
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)
