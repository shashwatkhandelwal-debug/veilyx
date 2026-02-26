# Proof Generator - The heart of Veilyx
# This creates the proof object that gets returned to the company
# Notice: no personal data is included in the proof

import uuid
from datetime import datetime, timedelta

def generate_proof(company_name, user_id, verification_results, consent_given):
    proof = {
        "verification_id": str(uuid.uuid4()),
        "requested_by": company_name,
        "user_id": user_id,
        "user_consent": consent_given,
        "attributes_verified": verification_results,
        "raw_data_shared": False,
        "proof_generated_at": datetime.now().isoformat(),
        "proof_valid_until": (datetime.now() + timedelta(hours=24)).isoformat(),
        "status": "VERIFIED" if all(verification_results.values()) else "FAILED"
    }
    return proof