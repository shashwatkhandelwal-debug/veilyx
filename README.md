# Veilyx
### Verification infrastructure for India. Proofs, not documents.

 <img width="1890" height="961" alt="Veilyx Dashboard" src="https://github.com/user-attachments/assets/5c732d80-f453-4390-af04-2dd69775eafd" />

---

## Why I built this

I was reading about the HDFC Bank data leak and something clicked. Why are companies collecting and storing actual Aadhaar cards, PAN numbers and bank statements just to verify someone is over 18 or has a valid document?

They don't need the document. They need the answer.

That's what Veilyx does. A company asks "is this user above 18?" and gets back a cryptographic proof: yes or no, verified, timestamped, signed. No raw data ever leaves the user's device. No documents stored on company servers. No breach liability.

India's DPDP Act is now in force. Companies that store unnecessary personal data are going to get hit hard. Veilyx makes compliance the default, not an afterthought.

---

## Who it's for

Any app that verifies user identity. If you're asking users to upload an Aadhaar copy, store a PAN number or collect any personal document just to answer a yes or no question, Veilyx is built for you.

Current use cases:
- Real Money Gaming apps that need age verification before allowing cash tables
- Dating platforms that need to confirm users are adults
- Fintech and lending apps doing KYC before onboarding
- BNPL platforms verifying user identity at checkout
- Insurance aggregators confirming policyholder details
- Any age-gated content platform under DPDP obligations

The verification runs entirely on the user's device. Only a cryptographic proof gets returned to your backend. The document never moves. The use case doesn't matter, the architecture is the same.

---

## What it does

Veilyx is a B2B identity verification API and SDK. Companies integrate it, send a verification request with user consent, and get back a proof object — not a document.

```json
{
  "verification_id": "d2698a21-9cbe-4ba6-9ea4-033d5006ac4c",
  "requested_by": "RummyKing Pro",
  "device_id": "a5b471d3-c230-4398-a97a-6b6baba190b2",
  "attributes_verified": {
    "age_above_18": true
  },
  "raw_data_shared": false,
  "status": "VERIFIED",
  "timestamp": "2026-03-04T02:42:03.134513"
}
```

Notice: `raw_data_shared: false`. Always.

---

## How it works

The verification flow has four steps:

1. **Device registration** — on app launch, the SDK generates an RSA/P256 key pair inside the hardware secure enclave (AndroidKeyStore on Android, iOS Secure Enclave on iPhone). The private key never leaves the device. The public key is registered with the Veilyx backend.

2. **Local verification** — when the app requests a proof, the user's Aadhaar Offline XML is parsed entirely on-device. The DOB is extracted locally and age is computed. No document is transmitted anywhere.

3. **Cryptographic signing** — the verification result is assembled into a proof payload and signed using the hardware-backed private key. The signature is mathematically unique to that device.

4. **Backend verification** — the signed proof is sent to POST /verify. The backend checks the cryptographic signature against the registered public key. If valid, the proof is authentic. Tampered proofs are rejected instantly.

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend API | Python 3.14 / FastAPI / slowapi |
| Database | SQLite (persistent device registry + verification logs) |
| Cryptography | Python cryptography library — RSA-2048 + P256 ECDSA |
| Android SDK | Kotlin / AndroidKeyStore / Play Integrity API |
| iOS SDK | Swift / CryptoKit / Secure Enclave / iOS Keychain |
| React Native | veilyx-react-native SDK + Objective-C bridge |
| Demo App | RummyKing Pro (veilyx-gaming-demo) |

---

## API endpoints

| Method | Endpoint | Auth | What it does |
|--------|----------|------|--------------|
| GET | `/` | None | Health check |
| POST | `/company/register` | None | Register a company, receive API key |
| POST | `/device/register` | None | Register a device public key |
| POST | `/verify` | API Key | Verify a signed proof |
| GET | `/stats` | API Key | Verification analytics and billing |
| GET | `/logs` | API Key | Last 50 verification logs |
| GET | `/devices` | API Key | All registered devices |
| GET | `/dashboard` | API Key (query param) | Live verification dashboard |
| GET | `/docs` | None | Interactive Swagger UI |

---

## SDK Methods

| Method | Platform | What it does |
|--------|----------|--------------|
| `initialize()` | Android, iOS | Generates hardware-backed key pair, returns deviceId and public key |
| `requestProof(request)` | Android, iOS | Runs local verification, returns signed proof |
| `pickAadhaarFile()` | Android, iOS | Opens native file picker, user selects Aadhaar XML, returns file contents |
| `readAadhaarFile(filePath)` | Android, iOS | Reads Aadhaar XML from a known file path, returns file contents |

### Usage example
```typescript
// Initialize on app start
const { deviceId, publicKeyPem } = await Veilyx.initialize();

// Let user pick their Aadhaar XML securely
const aadhaarXml = await Veilyx.pickAadhaarFile();

// Request age verification proof
const proof = await Veilyx.requestProof({
  companyName: 'YourApp',
  checks: ['age_above_18'],
  aadhaarXml: aadhaarXml
});

// Send proof to your backend for verification
// POST /verify with X-API-Key header
```

The Aadhaar XML file never leaves the device. Only the cryptographic proof is transmitted.
## Authentication

Protected endpoints require an `X-API-Key` header:

```bash
curl -X POST http://127.0.0.1:8000/verify \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"proof_payload": {...}, "signature": "..."}'
```

Register a company to get an API key:

```bash
curl -X POST http://127.0.0.1:8000/company/register \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Your Company"}'
```

---

## Verification checks supported

- `age_above_18` — confirms user is 18 or older based on Aadhaar Offline XML DOB
- `name_match` — matches user's name against company-provided name
- `document_valid` — confirms document hasn't been flagged invalid

---

## Pricing

₹4 per successful verification. Billed per API call. Visible in your dashboard.

---

## How to run it

**Requirements**
- Python 3.10+

**Install dependencies**
```bash
pip install -r requirements.txt
```

**Start the server**
```bash
python -m uvicorn api:app --reload
```

**Run the full test suite**
```bash
python test_sdk_simulation.py
```

**Open the API docs**
```
http://127.0.0.1:8000/docs
```

**Open the dashboard**
```
http://127.0.0.1:8000/dashboard?api_key=YOUR_API_KEY
```

---

## Rate limiting

| Endpoint | Limit |
|----------|-------|
| `/verify` | 20 requests/minute |
| `/device/register` | 5 requests/minute |
| `/company/register` | 3 requests/minute |
| `/stats`, `/logs`, `/devices`, `/dashboard` | 10 requests/minute |

---

## Project structure

```
veilyx/
├── api.py                              # FastAPI backend — all endpoints, auth, rate limiting
├── verification_engine.py              # Age, name, document check logic
├── Proof_generator.py                  # Builds the proof object returned to companies
├── mock_digilocker.py                  # 12 test users with DOB and document data
├── test_sdk_simulation.py              # Full end to end cryptographic simulation test
├── requirements.txt
├── veilyx-react-native/                # React Native SDK package
│   ├── src/index.ts                    # Public API surface
│   ├── android/.../VeilyxModule.kt     # Android KeyStore + Aadhaar XML parsing
│   ├── ios/Veilyx.swift                # iOS Secure Enclave + Keychain persistence
│   └── ios/Veilyx.m                    # Objective-C bridge
└── veilyx-gaming-demo/                 # Integrator demo app
    └── App.tsx                         # RummyKing Pro — full 4 step verification flow
```

---

## Test results

```
=== VEILYX SDK SIMULATION STARTED ===
[SUCCESS] SDK Initialized for Device: <uuid>
[SUCCESS] Company registered with API key: xxxxxxxx...
[SUCCESS] Server registered device: {status: SUCCESS}
[INFO] SDK generated signed Proof. Sending to Integrator backend.
=== VEILYX VERIFICATION RESULT ===
{ "valid": true, "message": "Cryptographic signature verified successfully." }
--- MALICIOUS ATTEMPT: Altering Payload without resigning ---
{ "valid": false, "message": "CRITICAL: Signature verification failed." }
```

Tamper detection confirmed working — modified proofs are rejected every time.

---

## The philosophy

India's DPDP Act exists because companies have been collecting data they don't need and storing it insecurely. Veilyx flips the model: verification without collection. Companies get compliance by default. Users keep their data.

Built by Shashwat Khandelwal.

