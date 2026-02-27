# api.py - Veilyx FastAPI Layer
# This turns Veilyx into a real API that companies can call

from fastapi import FastAPI
from pydantic import BaseModel
from mock_digilocker import get_user_data
from verification_engine import verify_user
from Proof_generator import generate_proof
from datetime import datetime

app = FastAPI()
proof_store = {}
request_log = []

# This defines what a verification request looks like
class VerificationRequest(BaseModel):
    user_id: str
    company_name: str
    requested_checks: list
    company_provided_name: str = None
    consent: bool

# This is the main endpoint companies will call
@app.post("/verify")
def verify(request: VerificationRequest):

    if not request.consent:
        return {"status": "DENIED", "reason": "User did not consent"}

    user_data = get_user_data(request.user_id)
    if not user_data:
        return {"status": "FAILED", "reason": "User not found"}

    results = verify_user(
        user_data,
        requested_checks=request.requested_checks,
        company_provided_name=request.company_provided_name
    )

    proof = generate_proof(
        company_name=request.company_name,
        user_id=request.user_id,
        verification_results=results,
        consent_given=request.consent
    )

    request_log.append({
        "timestamp": datetime.now().isoformat(),
        "company": request.company_name,
        "user_id": request.user_id,
        "checks_requested": request.requested_checks,
        "consent_given": request.consent,
        "result": proof["status"]
    })

    proof_store[proof["verification_id"]] = proof
    return proof

@app.get("/")
def home():
    return {
        "name": "Veilyx API",
        "version": "0.1.0",
        "description": "Verification infrastructure that returns proofs, not documents.",
        "status": "running",
        "endpoints": {
            "verify": "/verify",
            "docs": "/docs"
        },
        "philosophy": "Companies should receive verification proofs, not documents."
    }

@app.get("/status/{verification_id}")
def check_status(verification_id: str):

    if verification_id not in proof_store:
        return {
            "verification_id": verification_id,
            "status": "NOT_FOUND",
            "message": "No proof found with this ID"
        }

    proof = proof_store[verification_id]
    expiry = datetime.fromisoformat(proof["proof_valid_until"])
    now = datetime.now()

    if now > expiry:
        return {
            "verification_id": verification_id,
            "status": "EXPIRED",
            "message": "Proof expired. Request new verification."
        }

    remaining = expiry - now
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)

    return {
        "verification_id": verification_id,
        "status": "ACTIVE",
        "expires_in": f"{hours} hours and {minutes} minutes remaining",
        "requested_by": proof["requested_by"],
        "original_status": proof["status"]
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Veilyx API",
        "version": "0.1.0"
    }

@app.get("/audit-log")
def get_audit_log():
    return {
        "total_requests": len(request_log),
        "log": request_log
    }