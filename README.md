# Bakery Service RESTful API & Swagger UI

Dokumentasi teknis RESTful API Bakery Service untuk operasional penjualan produk roti dan pastry, pengelolaan data pelanggan, transaksi pemesanan, serta pemrosesan pembayaran.

---

## 🌐 Akses Dokumentasi & Pengujian Interaktif

Server saat ini **aktif** dan dapat diakses melalui peramban:

- 📖 **Swagger UI:** [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
- 📚 **ReDoc Documentation:** [http://127.0.0.1:8080/redoc](http://127.0.0.1:8080/redoc)
- 📄 **Spesifikasi OpenAPI 3.1 JSON:** [openapi.json](file:///Users/apple/Programming/Learning/Courses/iak/openapi.json)

Untuk menjalankan server secara manual:
```bash
python3 main.py
```

---

## 🏛️ Struktur Sumber Daya (Resources) & Endpoint

### 1. Customers (`/v1/customers`)
- `POST /v1/customers` : Mendaftarkan Pelanggan
- `GET /v1/customers/{customer_id}` : Detail Pelanggan

### 2. Products (`/v1/products`)
- `GET /v1/products` : Daftar Produk (mendukung filter kategori)
- `GET /v1/products/{product_id}` : Detail Produk

### 3. Orders (`/v1/orders`)
- `POST /v1/orders` : Membuat Pesanan (mendukung header `Idempotency-Key` dan alokasi stok otomatis)
- `GET /v1/orders` : Daftar Pesanan (penomoran halaman berbasis kursor / *cursor-based pagination*)
- `GET /v1/orders/{order_id}` : Detail Pesanan
- `POST /v1/orders/{order_id}/cancel` : Membatalkan Pesanan (pengembalian alokasi stok produk)

### 4. Payments (`/v1/payments`)
- `POST /v1/payments` : Memproses Pembayaran (mendukung header `Idempotency-Key`)
- `GET /v1/payments/{payment_id}` : Detail Pembayaran
- `POST /v1/payments/{payment_id}/confirm` : Konfirmasi Pembayaran

---

## ⚙️ Standar Teknis

1. **Idempotensi (`Idempotency-Key`):**
   - Mendukung header `Idempotency-Key` (UUID v4) pada pembuatan pesanan dan pemrosesan pembayaran.
   - **Replay Identik:** Jika permintaan diulang dengan kunci dan payload yang sama, sistem mengembalikan data tersimpan pertama kali dengan header `Idempotent-Replay: true`.
   - **Konflik (409):** Jika kunci yang sama digunakan ulang dengan parameter berbeda, sistem mengembalikan respons `HTTP 409 Conflict`.

2. **Penomoran Halaman (Cursor-Based Pagination):**
   - Menggunakan parameter `limit`, `starting_after`, dan `ending_before`.
   - Respons dibungkus dalam *envelope* terstruktur:
     ```json
     {
       "object": "list",
       "url": "/v1/orders",
       "has_more": true,
       "data": [ ... ]
     }
     ```

3. **Format Kesalahan (RFC 7807 / RFC 9457):**
   - Menghasilkan format pesan terstruktur yang dapat diproses oleh mesin dan dipahami oleh pengembang:
     ```json
     {
       "error": {
         "type": "invalid_request_error",
         "code": "idempotency_conflict",
         "message": "Keys for idempotent requests cannot be reused with different request parameters or body.",
         "param": "Idempotency-Key"
       }
     }
     ```

---

## 🧪 Pengujian Otomatis

Jalankan script pengujian terotomasi untuk memverifikasi seluruh fungsionalitas:
```bash
python3 test_api.py
```
# iak-idempotensi
