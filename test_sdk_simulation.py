import uuid
from datetime import datetime
import json
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

print("=== VEILYX SDK SIMULATION STARTED ===")

# 1. SDK generates a keypair locally (secure enclave simulation)
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
public_key = private_key.public_key()
public_key_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

device_id = str(uuid.uuid4())
print(f"[SUCCESS] SDK Initialized for Device: {device_id}")

# 2. SDK Registers Device over network
reg_response = client.post("/device/register", json={
    "device_id": device_id,
    "public_key_pem": public_key_pem,
    "attestation_payload": "dummy_valid_attestation"
})
print("[SUCCESS] Server registered device:", reg_response.json())

# 3. App asks SDK for proof
print("\n--- Integrator app asks for age check ---")

# 4. SDK does verification locally
proof_payload = {
    "verification_id": str(uuid.uuid4()),
    "device_id": device_id,
    "requested_by": "QuickLoan Fintech",
    "attributes_verified": {"age_above_18": True},
    "timestamp": datetime.now().isoformat()
}

# 5. SDK signs the payload
payload_json = json.dumps(proof_payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
signature = private_key.sign(
    payload_json,
    padding.PKCS1v15(),
    hashes.SHA256()
)
signature_b64 = base64.b64encode(signature).decode('utf-8')

request_data = {
    "proof_payload": proof_payload,
    "signature": signature_b64
}

print(f"[INFO] SDK generated signed Proof. Sending to Integrator backend.\n")

# 6. Integrator Backend submits proof to Veilyx Backend
verify_response = client.post("/verify", json=request_data)

print("=== VEILYX VERIFICATION RESULT ===")
print(json.dumps(verify_response.json(), indent=2))

# 7. Malicious testing: Edit the payload
proof_payload["attributes_verified"] = {"age_above_18": False} # Emulate a hacked proof
hacked_payload_json = json.dumps(proof_payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
# Reuse older signature
hacked_request_data = {
    "proof_payload": proof_payload,
    "signature": signature_b64
}

print("\n--- MALICIOUS ATTEMPT: Altering Payload without resigning ---")
verify_response_hacked = client.post("/verify", json=hacked_request_data)
print(json.dumps(verify_response_hacked.json(), indent=2))
