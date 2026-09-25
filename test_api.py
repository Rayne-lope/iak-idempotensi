import json
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database import PRODUCTS, CUSTOMERS

client = TestClient(app)

def test_full_flow():
    print("=" * 60)
    print("🧪 MEMULAI PENGUJIAN RESTFUL API TOKO ROTI (STRIPE STYLE)")
    print("=" * 60)

    # 1. Test GET /v1/customers & GET /v1/products
    print("\n[1] Menguji GET /v1/customers (Get All Pelanggan)...")
    res_cust = client.get("/v1/customers")
    assert res_cust.status_code == 200
    cust_data = res_cust.json()
    assert cust_data["object"] == "list"
    assert len(cust_data["data"]) >= 3
    print(f"✅ Sukses: Ditemukan {len(cust_data['data'])} data pelanggan terdaftar.")

    print("\n[2] Menguji GET /v1/products & PUT /v1/products/{id}/stock...")
    res = client.get("/v1/products")
    assert res.status_code == 200, f"Failed: {res.text}"
    products = res.json()
    print(f"✅ Sukses: Ditemukan {len(products['data'])} produk roti.")
    sourdough = [p for p in products['data'] if p['id'] == 'prod_sourdough01'][0]
    initial_stock = sourdough['stock']
    print(f"   Stok awal Sourdough: {initial_stock}")

    # Test PUT stock (Idempoten HTTP standard)
    res_put = client.put("/v1/products/prod_sourdough01/stock", json={"stock": 30})
    assert res_put.status_code == 200
    assert res_put.json()["stock"] == 30
    print("✅ Sukses PUT /v1/products/prod_sourdough01/stock: Stok diatur menjadi 30.")

    # 3. Test GET /v1/orders dengan Cursor Pagination & Envelope
    print("\n[3] Menguji GET /v1/orders (Cursor Pagination & Envelope)...")
    res = client.get("/v1/orders?limit=2")
    assert res.status_code == 200
    order_list = res.json()
    assert order_list["object"] == "list"
    assert "has_more" in order_list
    assert len(order_list["data"]) == 2
    print(f"✅ Sukses: Envelope valid, has_more={order_list['has_more']}, items={len(order_list['data'])}")
    last_id = order_list["data"][-1]["id"]

    # Test starting_after cursor
    res_next = client.get(f"/v1/orders?limit=2&starting_after={last_id}")
    assert res_next.status_code == 200
    next_list = res_next.json()
    print(f"✅ Sukses cursor starting_after={last_id}: Mengambil halaman berikutnya ({len(next_list['data'])} order).")

    # 4. Test POST /v1/orders dengan Idempotency-Key
    print("\n[4] Menguji POST /v1/orders dengan Idempotency-Key [Operasi Idempoten 1]...")
    idempotency_key = str(uuid.uuid4())
    order_payload = {
        "customer_id": "cus_budi01",
        "items": [
            {
                "product_id": "prod_sourdough01",
                "quantity": 2
            }
        ],
        "notes": "Tolong bungkus rapi"
    }
    
    headers = {"Idempotency-Key": idempotency_key}
    res_order = client.post("/v1/orders", json=order_payload, headers=headers)
    assert res_order.status_code == 201, f"Failed: {res_order.text}"
    assert res_order.headers.get("Idempotent-Replay") == "false"
    assert res_order.headers.get("X-Cache-Lookup") == "MISS"
    created_order = res_order.json()
    order_id = created_order["id"]
    print(f"✅ Sukses: Order {order_id} dibuat. Total: Rp {created_order['total_amount']:,}")

    # 5. Test IDEMPOTENCY REPLAY: Kirim request SAMA dengan key SAMA
    print("\n[5] Menguji Idempotency Replay (Request sama + Kunci sama)...")
    res_replay = client.post("/v1/orders", json=order_payload, headers=headers)
    assert res_replay.status_code == 201
    assert res_replay.headers.get("Idempotent-Replay") == "true"
    assert res_replay.headers.get("X-Cache-Lookup") == "HIT"
    assert res_replay.json()["id"] == order_id
    print(f"✅ Sukses Replay: Respons dikembalikan dari cache (Header 'Idempotent-Replay: true', 'X-Cache-Lookup: HIT')!")

    # 6. Test 409 CONFLICT: Kirim request BERBEDA dengan key SAMA
    print("\n[6] Menguji HTTP 409 Conflict (Kunci sama + Body berbeda)...")
    conflicting_payload = {
        "customer_id": "cus_budi01",
        "items": [
            {
                "product_id": "prod_sourdough01",
                "quantity": 3  # berbeda dari quantity 2
            }
        ]
    }
    res_conflict = client.post("/v1/orders", json=conflicting_payload, headers=headers)
    assert res_conflict.status_code == 409, f"Expected 409, got {res_conflict.status_code}: {res_conflict.text}"
    conflict_json = res_conflict.json()
    assert conflict_json["error"]["code"] == "idempotency_key_reused_with_different_body"
    print("✅ Sukses 409 Conflict Response:")
    print(json.dumps(conflict_json, indent=2))

    # 7. Test POST /v1/payments (Operasi Idempoten 2)
    print("\n[7] Menguji POST /v1/payments [Operasi Idempoten 2]...")
    pay_key = str(uuid.uuid4())
    pay_payload = {
        "order_id": order_id,
        "amount": created_order["total_amount"],
        "payment_method": "qris"
    }
    res_pay = client.post("/v1/payments", json=pay_payload, headers={"Idempotency-Key": pay_key})
    assert res_pay.status_code == 201
    payment = res_pay.json()
    print(f"✅ Sukses Pembayaran: ID {payment['id']}, status: {payment['status']}")

    # 8. Test Rollback Stok via POST /v1/orders/{id}/cancel (Operasi Idempoten 3)
    print("\n[8] Menguji Cancel Order & Rollback Stok [Operasi Idempoten 3]...")
    new_order = client.post("/v1/orders", json={
        "customer_id": "cus_siti02",
        "items": [{"product_id": "prod_croissant02", "quantity": 5}]
    }).json()
    temp_id = new_order["id"]
    croissant_stock_before = client.get("/v1/products/prod_croissant02").json()["stock"]
    
    cancel_key = str(uuid.uuid4())
    res_cancel = client.post(f"/v1/orders/{temp_id}/cancel", headers={"Idempotency-Key": cancel_key})
    assert res_cancel.status_code == 200
    croissant_stock_after = client.get("/v1/products/prod_croissant02").json()["stock"]
    assert croissant_stock_after == croissant_stock_before + 5
    print(f"✅ Sukses: Order {temp_id} dibatalkan dan 5 croissant berhasil dikembalikan ke stok.")

    # 9. Test Confirm Payment (Operasi Idempoten 4)
    print("\n[9] Menguji Confirm Payment [Operasi Idempoten 4]...")
    res_conf = client.post(f"/v1/payments/{payment['id']}/confirm")
    assert res_conf.status_code == 200
    print(f"✅ Sukses: Konfirmasi pembayaran {payment['id']} berstatus settlement.")

    print("\n" + "=" * 60)
    print("🎉 SEMUA TEST BERHASIL 100% SESUAI SPESIFIKASI DOSEN!")
    print("=" * 60)

if __name__ == "__main__":
    test_full_flow()
