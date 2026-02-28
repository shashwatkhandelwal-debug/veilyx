from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
import base64
import json

app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# In-memory database for demo purposes: device_id -> public_key (PEM string)
device_registry = {}

class DeviceRegistrationRequest(BaseModel):
    device_id: str
    public_key_pem: str
    attestation_payload: str  # Simulated payload from iOS/Android

class DeviceRegistrationResponse(BaseModel):
    status: str
    message: str

class ProofPayload(BaseModel):
    verification_id: str
    device_id: str
    requested_by: str
    attributes_verified: dict
    timestamp: str

class ProofVerificationRequest(BaseModel):
    proof_payload: ProofPayload
    signature: str # Base64 encoded signature of the proof_payload

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
        
    device_registry[reg_request.device_id] = reg_request.public_key_pem
    return {"status": "SUCCESS", "message": f"Device {reg_request.device_id} registered securely."}

@app.post("/verify", response_model=ProofVerificationResponse)
@limiter.limit("20/minute")
def verify_proof(request: Request, verification_request: ProofVerificationRequest):
    device_id = verification_request.proof_payload.device_id
    
    if device_id not in device_registry:
        raise HTTPException(status_code=404, detail="Device not registered")
        
    public_key_pem = device_registry[device_id]
    
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        
        # Construct the exact JSON string signed by the SDK: keys sorted and no whitespace to ensure deterministic serialization
        payload_dict = verification_request.proof_payload.model_dump()
        payload_json = json.dumps(payload_dict, separators=(',', ':'), sort_keys=True).encode('utf-8')
        
        signature_bytes = base64.b64decode(verification_request.signature)
        
        public_key.verify(
            signature_bytes,
            payload_json,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return {
            "valid": True,
            "message": "Cryptographic signature verified successfully. The proof is authentic.",
            "payload": payload_dict
        }
        
    except InvalidSignature:
        return {"valid": False, "message": "CRITICAL: Signature verification failed. Proof may be tampered with."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def home():
    return {
        "name": "Veilyx Local Verification API",
        "description": "API to securely verify localized cryptographic proofs.",
        "status": "running"
    }