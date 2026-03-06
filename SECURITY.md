# Security

## Fixed

| ID | Vulnerability | Severity |
|----|--------------|----------|
| C1 | Replay attack — nonce system exists but SDK never calls GET /nonce | Critical |
| C2 | XML tag case bug — Poi vs POI — age always false on real Aadhaar | Critical |
| C3 | Dummy attestation tokens accepted — fake device registration possible | Critical |
| H1 | No proof timestamp freshness check — stale proofs accepted indefinitely | High |
| H2 | Cross-company injection — requested_by not validated against API key | High |
| H3 | SSRF via webhook — internal IPs and localhost accepted | High |
| M1 | XXE injection — explicit OWASP parser flags missing on XmlPullParser | Medium |
| M2 | API key exposed in URL on /dashboard — logged in server access logs | Medium |
| M3 | No timeout on iOS URLSession in handleDigiLockerCallback | Medium |
| L1 | Unused imports and dead variables in Kotlin and Python | Low |
| L2 | Deprecated @app.on_event startup in FastAPI | Low |

## In Progress

| ID | Vulnerability | Severity | Notes |
|----|--------------|----------|-------|
| H4 | veilyx:// deep link hijacking — any app can intercept DigiLocker auth code | High | Blocked on domain setup for Universal Links |
| H5 | 5x hardcoded localhost URLs — broken in production | High | Blocked on Railway deployment |
| H6 | DigiLocker credentials hardcoded as placeholder strings in source | High | Blocked on DigiLocker partner approval |

## Reporting

To report a vulnerability please open a GitHub Issue.

