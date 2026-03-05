# Veilyx
### Verification infrastructure for India  
**Proofs, not documents.**

![Python](https://img.shields.io/badge/python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-green)
![License](https://img.shields.io/badge/license-MIT-blue)
![Status](https://img.shields.io/badge/status-experimental-orange)

<img width="1890" height="961" alt="Veilyx Dashboard" src="https://github.com/user-attachments/assets/5c732d80-f453-4390-af04-2dd69775eafd" />

---

# Overview

Many apps need to verify user attributes such as **age or identity**.

Today this usually requires collecting sensitive documents such as Aadhaar or other government IDs.  
This creates major problems:

- privacy risks
- data breach liability
- regulatory overhead
- unnecessary storage of personal data

**Veilyx replaces document sharing with cryptographic proofs.**

Instead of sending documents, the user’s device generates a **signed proof** confirming a specific attribute (for example `age_above_18`). The application receives only the verification result — never the document itself.

Example:

```json
{
  "attributes_verified": {
    "age_above_18": true
  }
}
```

No identity document is transmitted or stored.

---

# Quick Example

```javascript
const proof = await Veilyx.requestProof({
  checks: ["age_above_18"]
})

await fetch("https://api.veilyx.com/verify", {
  method: "POST",
  headers: { "X-API-Key": API_KEY },
  body: JSON.stringify(proof)
})
```

Verification response:

```json
{
  "status": "VERIFIED",
  "attributes_verified": {
    "age_above_18": true
  }
}
```

---

# Architecture

```
User Device
   │
   │ Aadhaar Offline XML
   ▼
Local Verification (SDK)
   │
   │ Signed cryptographic proof
   ▼
Veilyx Backend
   │
   │ Signature validation
   ▼
Integrator App
```

The backend verifies **cryptographic signatures**, not documents.

---

# How It Works

## 1. Device Registration

The SDK generates a hardware-backed key pair inside the secure enclave.

Platforms:

- Android → AndroidKeyStore  
- iOS → Secure Enclave  

The **private key never leaves the device**.

The public key is registered with the Veilyx backend.

---

## 2. Local Verification

Aadhaar Offline XML is parsed **entirely on-device**.

Example:

```
DOB extracted locally
Age calculated locally
```

Only the verification result is used.

No document data is transmitted.

---

## 3. Cryptographic Signing

The SDK constructs a proof payload and signs it with the device private key.

Each proof is **cryptographically bound to that device**.

---

## 4. Backend Verification

The signed proof is sent to:

```
POST /verify
```

The backend:

- retrieves the registered device public key
- verifies the cryptographic signature
- rejects tampered proofs

---

# Trust Model

Veilyx minimizes data exposure.

The backend **never receives identity documents**.

It only receives:

- verification result
- device identifier
- cryptographic signature

This significantly reduces privacy and compliance risks.

---

# Use Cases

Veilyx is designed for apps that require **privacy-preserving verification**.

## Dating Apps 

Dating platforms must verify users are **18+** while avoiding collection of sensitive documents.

Veilyx allows apps to verify age without storing Aadhaar or other identity documents.

Benefits:

- prevents underage users
- reduces catfishing
- avoids storing identity documents
- enables verified profile badges

Example verification:

```json
{
  "attributes_verified": {
    "age_above_18": true
  }
}
```

---

## Gaming Platforms

Age verification for games that require **18+ players**.

---

## Marketplaces

Seller verification without storing government documents.

---

## Fintech Apps

Attribute-based verification with reduced compliance burden.

---

## Hiring Platforms

Identity verification for candidates during onboarding.

---

# Proof Object

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

---

# Tech Stack

| Layer | Technology |
|------|-------------|
| Backend API | Python 3.10+, FastAPI, slowapi |
| Database | SQLite (dev), PostgreSQL (production) |
| Cryptography | Python cryptography library (RSA-2048 + P256 ECDSA) |
| Android SDK | Kotlin, AndroidKeyStore, XmlPullParser, Play Integrity API |
| iOS SDK | Swift, CryptoKit, Secure Enclave |
| React Native bridge | Objective-C |
| Demo app | React Native |

---

# API Endpoints

| Method | Endpoint | Auth | Description |
|------|------|------|------|
| GET | `/` | None | Health check |
| POST | `/company/register` | None | Register company |
| POST | `/device/register` | None | Register device public key |
| GET | `/nonce` | API Key | Get replay-protection nonce |
| POST | `/verify` | API Key | Verify signed proof |
| GET | `/stats` | API Key | Verification analytics |
| GET | `/logs` | API Key | Verification logs |
| GET | `/devices` | API Key | Registered devices |
| GET | `/dashboard` | API Key | Live verification dashboard |
| POST | `/webhooks/register` | API Key | Register webhook |
| GET | `/webhooks` | API Key | List webhooks |
| DELETE | `/nonce/cleanup` | API Key | Delete expired nonces |
| GET | `/digilocker/auth` | None | Start DigiLocker OAuth |
| GET | `/digilocker/callback` | None | DigiLocker callback |
| GET | `/digilocker/status` | None | DigiLocker configuration |
| DELETE | `/digilocker/cleanup` | API Key | Cleanup OAuth states |
| GET | `/docs` | None | Swagger docs |

---

# SDK Methods

| Method | Platform | Description |
|------|------|------|
| `initialize()` | Android, iOS | Generate device key pair |
| `requestProof()` | Android, iOS | Generate signed proof |
| `pickAadhaarFile()` | Android, iOS | Open file picker |
| `readAadhaarFile()` | Android, iOS | Read Aadhaar XML |
| `handleDigiLockerCallback()` | Android, iOS | Handle OAuth callback |
| `handleDeepLink()` | Android, iOS | Parse deep link |

---

# Authentication

All protected endpoints require:

```
X-API-Key: your_api_key_here
```

Register company:

```bash
curl -X POST https://your-backend.railway.app/company/register \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Your Company"}'
```

Verify proof:

```bash
curl -X POST https://your-backend.railway.app/verify \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"proof_payload": {}, "signature": ""}'
```

---

# Webhooks

Webhook requests include:

```
X-Veilyx-Signature
```

An HMAC-SHA256 signature of the payload body.

Example registration:

```bash
curl -X POST https://your-backend.railway.app/webhooks/register \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-server.com/webhook"}'
```

---

# Rate Limiting

| Endpoint | Limit |
|------|------|
| `/verify` | 20 req/min |
| `/device/register` | 5 req/min |
| `/company/register` | 3 req/min |
| `/nonce` | 30 req/min |
| `/stats` `/logs` `/devices` | 10 req/min |

---

# Running Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Run API:

```bash
python -m uvicorn api:app --reload
```

Run SDK simulation:

```bash
python test_sdk_simulation.py
```

Docs available at:

```
http://127.0.0.1:8000/docs
```

---

# Project Structure

```
veilyx/
├── api.py
├── test_sdk_simulation.py
├── requirements.txt
├── veilyx-react-native/
│   ├── src/index.ts
│   ├── android/.../VeilyxModule.kt
│   ├── ios/Veilyx.swift
│   └── ios/Veilyx.m
└── veilyx-gaming-demo/
    └── App.tsx
```

---

# Security Audit

| ID | Issue | Severity | Status |
|----|------|------|------|
| C2 | XML tag case bug | Critical | Fixed |
| C3 | Fake device registration | Critical | Fixed |
| H1 | Proof timestamp freshness | High | Fixed |
| H2 | Cross-company injection | High | Fixed |
| H3 | Webhook SSRF | High | Fixed |
| M1 | XXE injection | Medium | Fixed |
| M2 | API key exposure in dashboard URL | Medium | Fixed |
| M3 | iOS network timeout | Medium | Fixed |
| L1 | Dead imports | Low | Fixed |
| L2 | Deprecated FastAPI startup event | Low | Fixed |
| C1 | Replay attack (nonce unused) | Critical | Pending |
| H4 | Deep link hijacking | High | Pending |
| H5 | Hardcoded localhost URLs | High | Pending |
| H6 | DigiLocker credentials placeholder | High | Pending |

---

# Roadmap

- Deploy backend to Railway
- Replace localhost URLs with environment variables
- Configure DigiLocker OAuth credentials
- Implement mandatory nonce validation
- Replace custom deep links with Universal Links / Android App Links
- Implement UIDAI XML signature verification
- Validate Play Integrity tokens
- Validate Apple App Attest tokens
- Add certificate pinning

---

# Pricing

**₹4 per successful verification**

Usage-based billing.

---

# License

MIT License
