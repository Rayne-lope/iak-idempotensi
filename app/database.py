import time
from typing import Dict, List, Optional

# In-memory stores
CUSTOMERS: Dict[str, dict] = {}
PRODUCTS: Dict[str, dict] = {}
ORDERS: Dict[str, dict] = {}
PAYMENTS: Dict[str, dict] = {}

def init_db():
    CUSTOMERS.clear()
    PRODUCTS.clear()
    ORDERS.clear()
    PAYMENTS.clear()

    # Initial customers
    CUSTOMERS["cus_budi01"] = {
        "id": "cus_budi01",
        "object": "customer",
        "name": "Budi Santoso",
        "phone": "081234567890",
        "email": "budi.santoso@example.com",
        "created": int(time.time()) - 86400
    }
    CUSTOMERS["cus_siti02"] = {
        "id": "cus_siti02",
        "object": "customer",
        "name": "Siti Rahmawati",
        "phone": "089876543210",
        "email": "siti.rahma@example.com",
        "created": int(time.time()) - 43200
    }
    CUSTOMERS["cus_anita03"] = {
        "id": "cus_anita03",
        "object": "customer",
        "name": "Anita Wijaya",
        "phone": "085671234567",
        "email": "anita.w@example.com",
        "created": int(time.time()) - 10000
    }

    # Initial bakery products
    PRODUCTS["prod_sourdough01"] = {
        "id": "prod_sourdough01",
        "object": "product",
        "name": "Artisan Sourdough Country Loaf",
        "category": "bread",
        "unit_price": 45000,
        "stock": 25,
        "description": "Roti sourdough ragi alami fermentasi 24 jam dengan kerak renyah."
    }
    PRODUCTS["prod_croissant02"] = {
        "id": "prod_croissant02",
        "object": "product",
        "name": "French Butter Croissant",
        "category": "pastry",
        "unit_price": 25000,
        "stock": 40,
        "description": "Pastry lapis mentega Prancis AOP wangi, renyah di luar dan lembut di dalam."
    }
    PRODUCTS["prod_baguette03"] = {
        "id": "prod_baguette03",
        "object": "product",
        "name": "Classic Traditional Baguette",
        "category": "bread",
        "unit_price": 20000,
        "stock": 18,
        "description": "Roti baguette panjang klasik khas Prancis dengan tekstur berongga."
    }
    PRODUCTS["prod_cinnamon04"] = {
        "id": "prod_cinnamon04",
        "object": "product",
        "name": "Cream Cheese Cinnamon Roll",
        "category": "pastry",
        "unit_price": 28000,
        "stock": 30,
        "description": "Roti gulung kayu manis lembut dilapisi glasur cream cheese manis gurih."
    }

    # Pre-seeded orders for cursor pagination demonstration
    ORDERS["ord_20260925_001"] = {
        "id": "ord_20260925_001",
        "object": "order",
        "customer": "cus_budi01",
        "status": "completed",
        "currency": "idr",
        "items": [
            {
                "product_id": "prod_sourdough01",
                "name": "Artisan Sourdough Country Loaf",
                "unit_price": 45000,
                "quantity": 1,
                "subtotal": 45000
            }
        ],
        "total_amount": 45000,
        "notes": "Pesanan pagi",
        "created": int(time.time()) - 7200
    }
    ORDERS["ord_20260925_002"] = {
        "id": "ord_20260925_002",
        "object": "order",
        "customer": "cus_budi01",
        "status": "pending_baking",
        "currency": "idr",
        "items": [
            {
                "product_id": "prod_sourdough01",
                "name": "Artisan Sourdough Country Loaf",
                "unit_price": 45000,
                "quantity": 2,
                "subtotal": 90000
            },
            {
                "product_id": "prod_croissant02",
                "name": "French Butter Croissant",
                "unit_price": 25000,
                "quantity": 3,
                "subtotal": 75000
            }
        ],
        "total_amount": 165000,
        "notes": "Tolong dipotong slice tebal",
        "created": int(time.time()) - 3600
    }
    ORDERS["ord_20260925_003"] = {
        "id": "ord_20260925_003",
        "object": "order",
        "customer": "cus_siti02",
        "status": "ready_for_pickup",
        "currency": "idr",
        "items": [
            {
                "product_id": "prod_baguette03",
                "name": "Classic Traditional Baguette",
                "unit_price": 20000,
                "quantity": 1,
                "subtotal": 20000
            }
        ],
        "total_amount": 20000,
        "notes": None,
        "created": int(time.time()) - 1800
    }
    ORDERS["ord_20260925_004"] = {
        "id": "ord_20260925_004",
        "object": "order",
        "customer": "cus_anita03",
        "status": "paid",
        "currency": "idr",
        "items": [
            {
                "product_id": "prod_cinnamon04",
                "name": "Cream Cheese Cinnamon Roll",
                "unit_price": 28000,
                "quantity": 4,
                "subtotal": 112000
            }
        ],
        "total_amount": 112000,
        "notes": "Hangatkan sebelum diambil",
        "created": int(time.time()) - 600
    }

    # Initial payment
    PAYMENTS["pay_trx_001"] = {
        "id": "pay_trx_001",
        "object": "payment",
        "order_id": "ord_20260925_001",
        "amount": 45000,
        "currency": "idr",
        "payment_method": "qris",
        "status": "settlement",
        "created": int(time.time()) - 7100
    }

# Initialize on module import
init_db()
