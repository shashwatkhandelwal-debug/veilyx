# api.py - Veilyx FastAPI Layer
# This turns Veilyx into a real API that companies can call

from fastapi import FastAPI
from pydantic import BaseModel
from mock_digilocker import get_user_data
from verification_engine import verify_user
from Proof_generator import generate_proof

app = FastAPI()

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
    
    # Step 1 - Check consent
    if not request.consent:
        return {"status": "DENIED", "reason": "User did not consent"}
    
    # Step 2 - Get user data from mock DigiLocker
    user_data = get_user_data(request.user_id)
    if not user_data:
        return {"status": "FAILED", "reason": "User not found"}
    
    # Step 3 - Run verification
    results = verify_user(
        user_data,
        requested_checks=request.requested_checks,
        company_provided_name=request.company_provided_name
    )
    
    # Step 4 - Generate and return proof
    proof = generate_proof(
        company_name=request.company_name,
        user_id=request.user_id,
        verification_results=results,
        consent_given=request.consent
    )
    
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