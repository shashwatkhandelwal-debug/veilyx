# Veilyx

**Verification infrastructure that returns proofs, not documents.**

---

## Why I built this

I was reading about the HDFC Bank data leak and something clicked — why are companies collecting and storing actual Aadhaar cards, PAN numbers, and bank statements just to verify someone is over 18 or has a valid document?

They don't need the document. They need the answer.

That's what Veilyx does. A company asks "is this user above 18?" and gets back a cryptographic proof — yes or no, verified, timestamped, signed. No raw data ever leaves the user's side. No documents stored on company servers. No breach liability.

I also read about India's DPDP Act coming into force. Companies that store unnecessary personal data are going to get hit hard. Veilyx makes compliance the default, not an afterthought.

---

## What it does

Veilyx is a B2B identity verification API. Companies integrate it, send a verification request with user consent, and get back a **proof object** — not a document.

```json
{
  "verification_id": "d2698a21-9cbe-4ba6-9ea4-033d5006ac4c",
  "requested_by": "QuickLoan Fintech",
  "user_id": "user_001",
  "user_consent": true,
  "attributes_verified": {
    "age_above_18": true
  },
  "raw_data_shared": false,
  "status": "VERIFIED",
  "proof_valid_until": "2026-02-28T23:51:35.435872"
}
```

Notice: `raw_data_shared: false`. Always.

---

## Endpoints

| Method | Endpoint | What it does |
|--------|----------|--------------|
| POST | `/verify` | Run a verification, get back a proof |
| GET | `/status/{verification_id}` | Check if a proof is still valid |
| GET | `/health` | Server health check |
| GET | `/audit-log` | See all verification requests |
| GET | `/users` | List test users (dev only) |
| GET | `/docs` | Interactive API docs (Swagger UI) |

---

## Verification checks supported

- `age_above_18` — confirms user is 18 or older
- `name_match` — matches user's name against company-provided name
- `document_valid` — confirms document hasn't been flagged invalid

---

## How to run it

**Requirements**
- Python 3.8+
- FastAPI
- Uvicorn
- slowapi

**Install dependencies**
```bash
pip install fastapi uvicorn slowapi pydantic
```

**Start the server**
```bash
python -m uvicorn api:app --reload
```

**Open the docs**
```
http://127.0.0.1:8000/docs
```

---

## Rate limiting

`/verify` is rate limited to **10 requests per minute** per IP. Exceeding this returns:

```json
{
  "error": "Rate limit exceeded: 10 per 1 minute"
}
```

---

## Project structure

```
veilyx/
├── api.py                 # FastAPI layer — all endpoints live here
├── verification_engine.py # Runs the actual checks on user data
├── Proof_generator.py     # Builds the proof object returned to companies
├── mock_digilocker.py     # Simulates DigiLocker responses for testing
└── main.py                # Local test script to simulate the full flow
```

---

## The philosophy

India's DPDP Act exists because companies have been collecting data they don't need and storing it insecurely. Veilyx flips the model — verification without collection. Companies get compliance by default. Users keep their data.

Built by Shashwat Khandelwal.
