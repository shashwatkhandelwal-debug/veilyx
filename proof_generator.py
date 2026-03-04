# Proof Generator - The heart of Veilyx
# This creates the proof object that gets returned to the company
# Notice: no personal data is included in the proof

import uuid
from datetime import datetime, timedelta

def generate_proof(company_name, user_id, verification_results, consent_given):
    proof = {
        "verification_id": str(uuid.uuid4()),
        "requested_by": company_name,
        "user_consent": consent_given,
        "attributes_verified": verification_results,
        "raw_data_shared": False,
        "proof_generated_at": datetime.now().isoformat(),
        "proof_valid_until": (datetime.now() + timedelta(hours=1)).isoformat(),
        "status": "VERIFIED" if len(verification_results) > 0 and all(verification_results.values()) else "FAILED"
    }
    return proof