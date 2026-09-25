import os
import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🥐 Server Toko Roti RESTful API aktif!")
    print(f"📖 Buka Swagger UI di browser: http://127.0.0.1:{port}/docs")
    print(f"📚 ReDoc documentation: http://127.0.0.1:{port}/redoc")
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)
