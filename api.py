from fastapi import FastAPI, HTTPException, Request, Depends, Header, Query
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
import html
import urllib.parse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
import base64
import json
import sqlite3
import os
import uuid
import secrets
import time

app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'veilyx.db')

DIGILOCKER_CLIENT_ID = "YOUR_CLIENT_ID_HERE"
DIGILOCKER_CLIENT_SECRET = "YOUR_CLIENT_SECRET_HERE"
DIGILOCKER_REDIRECT_URI = "http://127.0.0.1:8000/digilocker/callback"
DIGILOCKER_AUTH_URL = "https://api.digitallocker.gov.in/public/oauth2/1/authorize"
DIGILOCKER_TOKEN_URL = "https://api.digitallocker.gov.in/public/oauth2/1/token"
DIGILOCKER_AADHAAR_URL = "https://api.digitallocker.gov.in/public/oauth2/1/xml/eaadhaar"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                public_key_pem TEXT,
                attestation_payload TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verification_id TEXT,
                device_id TEXT,
                requested_by TEXT,
                attributes_verified TEXT,
                timestamp TEXT,
                is_valid INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                company_id TEXT PRIMARY KEY,
                company_name TEXT,
                api_key TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                created_at REAL,
                used INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
    finally:
        conn.close()

def get_company_by_api_key(api_key: str):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM companies WHERE api_key = ? AND is_active = 1", (api_key,))
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        if row:
            return dict(zip(columns, row))
        return None
    finally:
        conn.close()

def verify_api_key(api_key: str = Header(..., alias='X-API-Key')):
    company = get_company_by_api_key(api_key)
    if not company:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    return company

init_db()

@app.on_event('startup')
def startup_event():
    init_db()

class DeviceRegistrationRequest(BaseModel):
    device_id: str = Field(..., min_length=1, description="Unique Device ID")
    public_key_pem: str = Field(..., min_length=50, description="RSA Public Key in PEM format")
    attestation_payload: str = Field(..., min_length=10, description="Simulated or real payload from iOS/Android")

class DeviceRegistrationResponse(BaseModel):
    status: str
    message: str

class ProofPayload(BaseModel):
    verification_id: str = Field(..., min_length=5)
    device_id: str = Field(..., min_length=1)
    requested_by: str = Field(..., min_length=1)
    attributes_verified: dict
    timestamp: str = Field(..., min_length=10)

class ProofVerificationRequest(BaseModel):
    proof_payload: ProofPayload
    signature: str = Field(..., min_length=10, description="Base64 encoded signature")

class ProofVerificationResponse(BaseModel):
    valid: bool
    message: str
    payload: dict = None

class CompanyRegistrationRequest(BaseModel):
    company_name: str = Field(..., min_length=1)

@app.post("/company/register")
@limiter.limit("3/minute")
def register_company(request: Request, body: CompanyRegistrationRequest):
    company_id = str(uuid.uuid4())
    api_key = secrets.token_urlsafe(32)
    
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT company_id FROM companies WHERE company_name = ?', (body.company_name,))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail='Company name already registered')
        cursor.execute('''
            INSERT INTO companies (company_id, company_name, api_key)
            VALUES (?, ?, ?)
        ''', (company_id, body.company_name, api_key))
        conn.commit()
    finally:
        conn.close()
        
    return {
        "company_id": company_id,
        "company_name": body.company_name,
        "api_key": api_key
    }

@app.post("/device/register", response_model=DeviceRegistrationResponse)
@limiter.limit("5/minute")
def register_device(request: Request, reg_request: DeviceRegistrationRequest):
    # In a real app, verify the 'attestation_payload' with Apple DeviceCheck / Google Play Integrity servers
    if not reg_request.attestation_payload:
        raise HTTPException(status_code=400, detail="Missing attestation payload")
        
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO devices (device_id, public_key_pem, attestation_payload)
            VALUES (?, ?, ?)
        ''', (reg_request.device_id, reg_request.public_key_pem, reg_request.attestation_payload))
        conn.commit()
    finally:
        conn.close()
        
    return {"status": "SUCCESS", "message": f"Device {reg_request.device_id} registered securely."}

@app.post("/verify", response_model=ProofVerificationResponse)
@limiter.limit("20/minute")
def verify_proof(request: Request, verification_request: ProofVerificationRequest, company: dict = Depends(verify_api_key)):
    device_id = verification_request.proof_payload.device_id
    
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT public_key_pem FROM devices WHERE device_id = ?', (device_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Device not registered")
        public_key_pem = row[0]
    finally:
        conn.close()
    
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        
        # Construct the exact JSON string signed by the SDK: keys sorted and no whitespace to ensure deterministic serialization
        payload_dict = verification_request.proof_payload.model_dump()
        payload_json = json.dumps(payload_dict, separators=(',', ':'), sort_keys=True).encode('utf-8')
        
        signature_bytes = base64.b64decode(verification_request.signature)
        
        if isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(
                signature_bytes,
                payload_json,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(
                signature_bytes,
                payload_json,
                ec.ECDSA(hashes.SHA256())
            )
        else:
            raise Exception("Unsupported public key type.")
        
        is_valid = 1
        response_data = {
            "valid": True,
            "message": "Cryptographic signature verified successfully. The proof is authentic.",
            "payload": payload_dict
        }
        
    except InvalidSignature:
        is_valid = 0
        response_data = {"valid": False, "message": "CRITICAL: Signature verification failed. Proof may be tampered with."}
    except Exception as e:
        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO verification_logs (verification_id, device_id, requested_by, attributes_verified, timestamp, is_valid)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                verification_request.proof_payload.verification_id,
                device_id,
                verification_request.proof_payload.requested_by,
                json.dumps(verification_request.proof_payload.attributes_verified),
                verification_request.proof_payload.timestamp,
                0
            ))
            conn.commit()
        finally:
            conn.close()
        raise HTTPException(status_code=500, detail=str(e))

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO verification_logs (verification_id, device_id, requested_by, attributes_verified, timestamp, is_valid)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            verification_request.proof_payload.verification_id,
            device_id,
            verification_request.proof_payload.requested_by,
            json.dumps(verification_request.proof_payload.attributes_verified),
            verification_request.proof_payload.timestamp,
            is_valid
        ))
        conn.commit()
    finally:
        conn.close()

    return response_data

@app.get("/stats")
@limiter.limit("10/minute")
def get_stats(request: Request, company: dict = Depends(verify_api_key)):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*),
                SUM(CASE WHEN is_valid = 1 THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_valid = 0 THEN 1 ELSE 0 END),
                MAX(created_at)
            FROM verification_logs
            WHERE requested_by = ?
        ''', (company['company_name'],))
        row = cursor.fetchone()
        total = row[0] or 0
        successful = row[1] or 0
        failed = row[2] or 0
        recent = row[3]
        
        success_rate = round((successful / total * 100), 2) if total > 0 else 0.0
        
        cursor.execute('SELECT requested_by, COUNT(*) FROM verification_logs WHERE requested_by = ? GROUP BY requested_by', (company['company_name'],))
        by_company = {r[0]: r[1] for r in cursor.fetchall()}
        
        return {
            "total_verifications": total,
            "successful_verifications": successful,
            "failed_verifications": failed,
            "tamper_attempts": failed,
            "success_rate": success_rate,
            "verifications_by_company": by_company,
            "most_recent_verification": recent
        }
    finally:
        conn.close()

@app.get("/devices")
@limiter.limit("10/minute")
def get_devices(request: Request, company: dict = Depends(verify_api_key)):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT d.device_id, d.attestation_payload, d.registered_at 
            FROM devices d
            WHERE d.device_id IN (
                SELECT DISTINCT device_id FROM verification_logs WHERE requested_by = ?
            )
            ORDER BY d.registered_at DESC
        ''', (company['company_name'],))
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()

@app.get("/logs")
@limiter.limit("10/minute")
def get_logs(request: Request, company: dict = Depends(verify_api_key)):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM verification_logs WHERE requested_by = ? ORDER BY created_at DESC LIMIT 50', (company['company_name'],))
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_company_by_api_key_query(api_key: str):
    company = get_company_by_api_key(api_key)
    if not company:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return company

@app.get("/dashboard", response_class=HTMLResponse)
@limiter.limit("10/minute")
def get_dashboard(request: Request, api_key: str):
    company = get_company_by_api_key_query(api_key)
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        
        # Stats
        cursor.execute('''
            SELECT 
                COUNT(*),
                SUM(CASE WHEN is_valid = 1 THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_valid = 0 THEN 1 ELSE 0 END)
            FROM verification_logs
            WHERE requested_by = ?
        ''', (company['company_name'],))
        row = cursor.fetchone()
        total = row[0] or 0
        successful = row[1] or 0
        failed = row[2] or 0
        success_rate = round((successful / total * 100), 2) if total > 0 else 0.0
        billing_amount = successful * 4
        
        # Logs
        cursor.execute('''
            SELECT verification_id, device_id, requested_by, attributes_verified, is_valid, created_at 
            FROM verification_logs
            WHERE requested_by = ?
            ORDER BY created_at DESC LIMIT 10
        ''', (company['company_name'],))
        logs = cursor.fetchall()

        # HTML Template Construction
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="30">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Veilyx Dashboard</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0a0a0a; color: #ffffff; margin: 0; padding: 20px; }}
                h1 {{ color: #FF6B00; }}
                h2 {{ color: #FF6B00; }}
                .stats-container {{ display: flex; gap: 20px; margin-bottom: 30px; }}
                .stat-box {{ background-color: #111111; padding: 20px; border-radius: 8px; flex: 1; text-align: center; border: 1px solid #FF6B00; }}
                .stat-value {{ font-size: 2em; font-weight: bold; margin-top: 10px; color: #FF6B00; }}
                table {{ width: 100%; border-collapse: collapse; background-color: #111111; border-radius: 8px; overflow: hidden; }}
                th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #222; }}
                th {{ background-color: #1a1a1a; color: #FF6B00; }}
                tr:hover {{ background-color: #1a1a1a; }}
                .valid {{ color: #FF6B00; font-weight: bold; }}
                .invalid {{ color: #f44336; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>Veilyx ⚡ Verification Dashboard</h1>
            <p style="border-left: 3px solid #FF6B00; padding-left: 10px;">Welcome, <strong>{html.escape(company['company_name'])}</strong></p>
            <p style="color: #888; font-size: 0.9em; margin-top: -10px;">Billing rate: ₹4 per successful verification</p>
            
            <div class="stats-container">
                <div class="stat-box">
                    <div>Total Verifications</div>
                    <div class="stat-value">{total}</div>
                </div>
                <div class="stat-box">
                    <div>Successful</div>
                    <div class="stat-value">{successful}</div>
                </div>
                <div class="stat-box">
                    <div>Tamper Attempts Blocked</div>
                    <div class="stat-value" style="color: #f44336;">{failed}</div>
                </div>
                <div class="stat-box">
                    <div>Success Rate</div>
                    <div class="stat-value">{success_rate}%</div>
                </div>
                <div class="stat-box">
                    <div>Total Billed</div>
                    <div class="stat-value">₹{billing_amount}</div>
                </div>
            </div>

            <h2>Recent Verifications</h2>
            <table>
                <thead>
                    <tr>
                        <th>Verification ID</th>
                        <th>Device ID</th>
                        <th>Attributes</th>
                        <th>Status</th>
                        <th>Timestamp</th>
                    </tr>
                </thead>
                <tbody>
        """
        for log in logs:
            status_class = "valid" if log[4] == 1 else "invalid"
            status_text = "VALID" if log[4] == 1 else "TAMPERED"
            html_content += f"""
                    <tr>
                        <td>{html.escape(str(log[0][:8]))}...</td>
                        <td>{html.escape(str(log[1][:8]))}...</td>
                        <td><code>{html.escape(str(log[3]))}</code></td>
                        <td class="{status_class}">{status_text}</td>
                        <td>{html.escape(str(log[5]))}</td>
                    </tr>
            """
            
        html_content += """
                </tbody>
            </table>
            <p style="text-align: center; color: #888; font-size: 0.9em; margin-top: 20px;">
                <em>Dashboard auto-refreshes every 30 seconds</em>
            </p>
        </body>
        </html>
        """
        return html_content
    finally:
        conn.close()

@app.get("/digilocker/auth")
@limiter.limit("10/minute")
def digilocker_auth(request: Request):
    state = secrets.token_urlsafe(16)
    
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO oauth_states (state, created_at) VALUES (?, ?)', (state, time.time()))
        conn.commit()
    finally:
        conn.close()
    
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": DIGILOCKER_CLIENT_ID,
        "redirect_uri": DIGILOCKER_REDIRECT_URI,
        "state": state,
        "scope": "openid"
    })
    auth_url = f"{DIGILOCKER_AUTH_URL}?{params}"
    
    return {"auth_url": auth_url, "state": state}


@app.get("/digilocker/callback")
async def digilocker_callback(request: Request, code: str = Query(...), state: str = Query(...)):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT created_at FROM oauth_states WHERE state = ? AND used = 0', (state,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail='Invalid or expired OAuth state')
        if time.time() - row[0] > 600:
            raise HTTPException(status_code=400, detail='OAuth state expired. Please try again.')
        cursor.execute('UPDATE oauth_states SET used = 1 WHERE state = ?', (state,))
        conn.commit()
    finally:
        conn.close()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Exchange authorization code for access token
            token_response = await client.post(
                DIGILOCKER_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": DIGILOCKER_REDIRECT_URI,
                    "client_id": DIGILOCKER_CLIENT_ID,
                    "client_secret": DIGILOCKER_CLIENT_SECRET
                }
            )
            
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"DigiLocker token exchange failed: {token_response.text}"
                )
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(status_code=502, detail="No access token received from DigiLocker")
            
            # Fetch Aadhaar XML using the access token
            aadhaar_response = await client.get(
                DIGILOCKER_AADHAAR_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if aadhaar_response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to fetch Aadhaar XML: {aadhaar_response.text}"
                )
            
            xml_content = aadhaar_response.text
            return {"aadhaar_xml": xml_content, "status": "SUCCESS"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DigiLocker integration error: {str(e)}")


@app.delete("/digilocker/cleanup")
def digilocker_cleanup(company: dict = Depends(verify_api_key)):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM oauth_states WHERE used = 1 OR ? - created_at > 600', (time.time(),))
        deleted_count = cursor.rowcount
        conn.commit()
        return {"status": "SUCCESS", "deleted_count": deleted_count}
    finally:
        conn.close()


@app.get("/digilocker/status")
def digilocker_status():
    if DIGILOCKER_CLIENT_ID != "YOUR_CLIENT_ID_HERE":
        return {"configured": True}
    return {
        "configured": False,
        "message": "DigiLocker credentials not configured. Replace YOUR_CLIENT_ID_HERE and YOUR_CLIENT_SECRET_HERE with real credentials from https://partners.digitallocker.gov.in"
    }


@app.get("/")
def home():
    return {
        "name": "Veilyx Local Verification API",
        "description": "API to securely verify localized cryptographic proofs.",
        "status": "running"
    }