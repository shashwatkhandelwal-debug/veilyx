import uuid
from datetime import datetime, timezone
import json
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def run_simulation():
    print("=== VEILYX SDK SIMULATION STARTED ===")

    # 1. Setup Identity
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    device_id = str(uuid.uuid4())
    print(f"[SDK] Keypair generated for Device: {device_id}")

    # 2. Register Company and Device
    unique_name = f"TestCorp_{uuid.uuid4().hex[:6]}"
    comp_resp = client.post("/company/register", json={"company_name": unique_name})
    api_key = comp_resp.json()["api_key"]
    print(f"[API] Registered {unique_name} (API Key: {api_key[:8]}...)")

    client.post("/device/register", json={
        "device_id": device_id,
        "public_key_pem": public_key_pem,
        "attestation_payload": "real_attestation_" + uuid.uuid4().hex
    })
    print(f"[API] Device registered")

    # 3. Standard Verification Flow
    print("\n--- TEST: Standard Verification Flow ---")
    headers = {"X-API-Key": api_key}
    nonce = client.get("/nonce", headers=headers).json()["nonce"]
    print(f"[API] Fetched nonce: {nonce}")

    proof_payload = {
        "verification_id": str(uuid.uuid4()),
        "device_id": device_id,
        "requested_by": unique_name,
        "attributes_verified": {"age_above_18": True},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nonce": nonce
    }
    payload_json = json.dumps(proof_payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
    sig = private_key.sign(payload_json, padding.PKCS1v15(), hashes.SHA256())
    
    verify_resp = client.post("/verify", headers=headers, json={
        "proof_payload": proof_payload,
        "signature": base64.b64encode(sig).decode('utf-8')
    })
    print(f"[API] Verification Result: {verify_resp.json().get('valid')}")

    # 4. Replay Attack Test (Same Nonce)
    print("\n--- TEST: Replay Attack (Same Nonce) ---")
    replay_resp = client.post("/verify", headers=headers, json={
        "proof_payload": proof_payload,
        "signature": base64.b64encode(sig).decode('utf-8')
    })
    print(f"[API] Blocked Replay? {replay_resp.status_code == 400} (Status: {replay_resp.status_code})")

    # 5. PVC Issuance Test
    print("\n--- TEST: Portable Verification Credential (PVC) ---")
    nonce2 = client.get("/nonce", headers=headers).json()["nonce"]
    pvc_payload = {
        "verification_id": str(uuid.uuid4()),
        "device_id": device_id,
        "requested_by": unique_name,
        "attributes_verified": {"age_above_18": True},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nonce": nonce2
    }
    pvc_payload_json = json.dumps(pvc_payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
    pvc_sig = private_key.sign(pvc_payload_json, padding.PKCS1v15(), hashes.SHA256())
    
    pvc_resp = client.post("/credential/issue", headers=headers, json={
        "proof_payload": pvc_payload,
        "signature": base64.b64encode(pvc_sig).decode('utf-8')
    })
    
    if pvc_resp.status_code == 200:
        print(f"[API] PVC Issued Successfully")
        print(json.dumps(pvc_resp.json(), indent=2))
    else:
        print(f"[ERROR] PVC Issuance failed: {pvc_resp.text}")

if __name__ == "__main__":
    run_simulation()
