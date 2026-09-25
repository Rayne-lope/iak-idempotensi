import hashlib
import json
import time
from typing import Dict, Any, Optional, Tuple
from fastapi import HTTPException

# Idempotency storage: key -> { "payload_hash": str, "status_code": int, "response_body": Any, "created_at": float }
IDEMPOTENCY_RECORDS: Dict[str, dict] = {}
EXPIRATION_SECONDS = 86400  # 24 jam ala Stripe

def compute_payload_hash(data: Any) -> str:
    """Computes a SHA-256 hash of canonical JSON data."""
    if isinstance(data, (bytes, str)):
        raw_bytes = data if isinstance(data, bytes) else data.encode("utf-8")
    else:
        raw_bytes = json.dumps(data, sort_keys=True, separators=(',', ':')).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()

def check_idempotency(key: str, payload_data: Any) -> Optional[Tuple[int, Any]]:
    """
    Checks if the key has been used before.
    Returns:
      - None if this is a fresh key
      - (status_code, response_body) if identical retry (should replay)
    Raises:
      - HTTPException(409) if the key exists but with different payload
    """
    now = time.time()
    if key in IDEMPOTENCY_RECORDS:
        record = IDEMPOTENCY_RECORDS[key]
        if now - record["created_at"] > EXPIRATION_SECONDS:
            del IDEMPOTENCY_RECORDS[key]
            return None

        current_hash = compute_payload_hash(payload_data)
        if record["payload_hash"] != current_hash:
            # Sesuai Slide 6, 10, 11 materi & modul dosen
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "https://api.example.com/errors/idempotency-conflict",
                    "error": {
                        "type": "invalid_request_error",
                        "code": "idempotency_key_reused_with_different_body",
                        "message": "Kunci idempotency sudah pernah dipakai dengan body berbeda. Sesuai standar RFC 7807 & Slide 14, request ini ditolak dengan kode 409.",
                        "param": "Idempotency-Key"
                    }
                }
            )
        return record["status_code"], record["response_body"]
    
    return None

def save_idempotency_record(key: str, payload_data: Any, status_code: int, response_body: Any):
    """Saves the execution result for this idempotency key."""
    IDEMPOTENCY_RECORDS[key] = {
        "payload_hash": compute_payload_hash(payload_data),
        "status_code": status_code,
        "response_body": response_body,
        "created_at": time.time()
    }
