from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
import base64
import json
import sqlite3
import os

app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'veilyx.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                public_key_pem TEXT,
                attestation_payload TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verification_id TEXT,
                device_id TEXT,
                requested_by TEXT,
                attributes_verified TEXT,
                timestamp TEXT,
                is_valid INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    finally:
        conn.close()

init_db()

@app.on_event('startup')
def startup_event():
    init_db()

class DeviceRegistrationRequest(BaseModel):
    device_id: str = Field(..., min_length=1, description="Unique Device ID")
    public_key_pem: str = Field(..., min_length=50, description="RSA Public Key in PEM format")
    attestation_payload: str = Field(..., min_length=10, description="Simulated or real payload from iOS/Android")

class DeviceRegistrationResponse(BaseModel):
    status: str
    message: str

class ProofPayload(BaseModel):
    verification_id: str = Field(..., min_length=5)
    device_id: str = Field(..., min_length=1)
    requested_by: str = Field(..., min_length=1)
    attributes_verified: dict
    timestamp: str = Field(..., min_length=10)

class ProofVerificationRequest(BaseModel):
    proof_payload: ProofPayload
    signature: str = Field(..., min_length=10, description="Base64 encoded signature")

class ProofVerificationResponse(BaseModel):
    valid: bool
    message: str
    payload: dict = None

@app.post("/device/register", response_model=DeviceRegistrationResponse)
@limiter.limit("5/minute")
def register_device(request: Request, reg_request: DeviceRegistrationRequest):
    # In a real app, verify the 'attestation_payload' with Apple DeviceCheck / Google Play Integrity servers
    if not reg_request.attestation_payload:
        raise HTTPException(status_code=400, detail="Missing attestation payload")
        
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO devices (device_id, public_key_pem, attestation_payload)
            VALUES (?, ?, ?)
        ''', (reg_request.device_id, reg_request.public_key_pem, reg_request.attestation_payload))
        conn.commit()
    finally:
        conn.close()
        
    return {"status": "SUCCESS", "message": f"Device {reg_request.device_id} registered securely."}

@app.post("/verify", response_model=ProofVerificationResponse)
@limiter.limit("20/minute")
def verify_proof(request: Request, verification_request: ProofVerificationRequest):
    device_id = verification_request.proof_payload.device_id
    
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT public_key_pem FROM devices WHERE device_id = ?', (device_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Device not registered")
        public_key_pem = row[0]
    finally:
        conn.close()
    
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        
        # Construct the exact JSON string signed by the SDK: keys sorted and no whitespace to ensure deterministic serialization
        payload_dict = verification_request.proof_payload.model_dump()
        payload_json = json.dumps(payload_dict, separators=(',', ':'), sort_keys=True).encode('utf-8')
        
        signature_bytes = base64.b64decode(verification_request.signature)
        
        if isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(
                signature_bytes,
                payload_json,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(
                signature_bytes,
                payload_json,
                ec.ECDSA(hashes.SHA256())
            )
        else:
            raise Exception("Unsupported public key type.")
        
        is_valid = 1
        response_data = {
            "valid": True,
            "message": "Cryptographic signature verified successfully. The proof is authentic.",
            "payload": payload_dict
        }
        
    except InvalidSignature:
        is_valid = 0
        response_data = {"valid": False, "message": "CRITICAL: Signature verification failed. Proof may be tampered with."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO verification_logs (verification_id, device_id, requested_by, attributes_verified, timestamp, is_valid)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            verification_request.proof_payload.verification_id,
            device_id,
            verification_request.proof_payload.requested_by,
            json.dumps(verification_request.proof_payload.attributes_verified),
            verification_request.proof_payload.timestamp,
            is_valid
        ))
        conn.commit()
    finally:
        conn.close()

    return response_data

@app.get("/stats")
@limiter.limit("10/minute")
def get_stats(request: Request):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*),
                SUM(CASE WHEN is_valid = 1 THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_valid = 0 THEN 1 ELSE 0 END),
                MAX(created_at)
            FROM verification_logs
        ''')
        row = cursor.fetchone()
        total = row[0] or 0
        successful = row[1] or 0
        failed = row[2] or 0
        recent = row[3]
        
        success_rate = round((successful / total * 100), 2) if total > 0 else 0.0
        
        cursor.execute('SELECT requested_by, COUNT(*) FROM verification_logs GROUP BY requested_by')
        by_company = {r[0]: r[1] for r in cursor.fetchall()}
        
        return {
            "total_verifications": total,
            "successful_verifications": successful,
            "failed_verifications": failed,
            "tamper_attempts": failed,
            "success_rate": success_rate,
            "verifications_by_company": by_company,
            "most_recent_verification": recent
        }
    finally:
        conn.close()

@app.get("/logs")
@limiter.limit("10/minute")
def get_logs(request: Request):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM verification_logs ORDER BY created_at DESC LIMIT 50')
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()

@app.get("/")
def home():
    return {
        "name": "Veilyx Local Verification API",
        "description": "API to securely verify localized cryptographic proofs.",
        "status": "running"
    }