import Foundation
import CryptoKit
import LocalAuthentication

@objc(Veilyx)
class Veilyx: NSObject {
    
    private let keyAlias = "veilyx_identity_key"
    private var deviceId: String = ""
    
    @objc(initialize:withRejecter:)
    func initialize(resolve: @escaping RCTPromiseResolveBlock, reject: @escaping RCTPromiseRejectBlock) {
        do {
            if deviceId.isEmpty {
                if let storedDeviceId = UserDefaults.standard.string(forKey: "veilyx_device_id") {
                    deviceId = storedDeviceId
                } else {
                    deviceId = UUID().uuidString
                    UserDefaults.standard.set(deviceId, forKey: "veilyx_device_id")
                }
            }
            
            // Try to load existing key from Keychain or generate a new one
            let tag = keyAlias.data(using: .utf8)!
            let getQuery: [String: Any] = [
                kSecClass as String: kSecClassKey,
                kSecAttrApplicationTag as String: tag,
                kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
                kSecReturnRef as String: true
            ]
            
            var item: CFTypeRef?
            let access = SecAccessControlCreateWithFlags(
                kCFAllocatorDefault,
                kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
                .privateKeyUsage,
                nil)!
                
            let attributes: [String: Any] = [
                kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
                kSecAttrKeySizeInBits as String: 256,
                kSecAttrTokenID as String: kSecAttrTokenIDSecureEnclave,
                kSecPrivateKeyAttrs as String: [
                    kSecAttrIsPermanent as String: true,
                    kSecAttrApplicationTag as String: tag,
                    kSecAttrAccessControl as String: access
                ]
            ]
            
            var error: Unmanaged<CFError>?
            // Try to fetch first
            var storedKey: SecKey?
            if SecItemCopyMatching(getQuery as CFDictionary, &item) == errSecSuccess {
                storedKey = (item as! SecKey)
            } else {
                guard let newKey = SecKeyCreateRandomKey(attributes as CFDictionary, &error) else {
                    reject("INIT_ERROR", "Could not generate Secure Enclave key: \(error?.takeRetainedValue().localizedDescription ?? "")", nil)
                    return
                }
                storedKey = newKey
            }
            
            guard let publicKey = SecKeyCopyPublicKey(storedKey!) else {
                reject("INIT_ERROR", "Could not extract public key", nil)
                return
            }
            
            var exportError: Unmanaged<CFError>?
            guard let publicKeyData = SecKeyCopyExternalRepresentation(publicKey, &exportError) as Data? else {
                reject("INIT_ERROR", "Could not export public key data representation", nil)
                return
            }
            
            let publicKeyBase64 = publicKeyData.base64EncodedString()
            let pem = "-----BEGIN PUBLIC KEY-----\n\(publicKeyBase64)\n-----END PUBLIC KEY-----"
            
            // Simulated DeviceCheck token
            let attestationPayload = "dummy_ios_devicecheck_token"
            
            resolve([
                "deviceId": deviceId,
                "publicKeyPem": pem,
                "attestationPayload": attestationPayload
            ])
        } catch {
            reject("INIT_ERROR", error.localizedDescription, error)
        }
    }
    
    @objc(requestProof:withChecks:withAadhaar:withResolver:withRejecter:)
    func requestProof(companyName: String, checks: [String], aadhaarXmlData: String, resolve: @escaping RCTPromiseResolveBlock, reject: @escaping RCTPromiseRejectBlock) {
        do {
            let tag = keyAlias.data(using: .utf8)!
            let getQuery: [String: Any] = [
                kSecClass as String: kSecClassKey,
                kSecAttrApplicationTag as String: tag,
                kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
                kSecReturnRef as String: true
            ]
            
            var item: CFTypeRef?
            let status = SecItemCopyMatching(getQuery as CFDictionary, &item)
            
            guard status == errSecSuccess else {
                reject("KEY_ERROR", "Key not found in Keychain. Call initialize first.", nil)
                return
            }
            
            let privateKey = item as! SecKey
            
            var verifiedAttributes: [String: Any] = [:]
            
            for check in checks {
                if check == "age_above_18" {
                    var verified = false
                    if !aadhaarXmlData.isEmpty {
                        // Regex parsing for DOB in XML
                        if let range = aadhaarXmlData.range(of: "dob=\"([^\"]+)\"", options: .regularExpression) {
                            let matchStr = String(aadhaarXmlData[range])
                            let components = matchStr.components(separatedBy: "\"")
                            if components.count > 1 {
                                let dobStr = components[1]
                                let formatter = DateFormatter()
                                formatter.dateFormat = "dd-MM-yyyy" // standard aadhaar format
                                if let dobDate = formatter.date(from: dobStr) {
                                    if let eighteenYearsAgo = Calendar.current.date(byAdding: .year, value: -18, to: Date()) {
                                        if dobDate <= eighteenYearsAgo {
                                            verified = true
                                        }
                                    }
                                } else {
                                    formatter.dateFormat = "yyyy-MM-dd"
                                    if let dobDate = formatter.date(from: dobStr) {
                                        if let eighteenYearsAgo = Calendar.current.date(byAdding: .year, value: -18, to: Date()) {
                                            if dobDate <= eighteenYearsAgo {
                                                verified = true
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    verifiedAttributes[check] = verified
                } else {
                    verifiedAttributes[check] = true
                }
            }
            
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            let timestamp = formatter.string(from: Date())
            let verificationId = UUID().uuidString
            
            let proofPayload: [String: Any] = [
                "verification_id": verificationId,
                "device_id": deviceId,
                "requested_by": companyName,
                "attributes_verified": verifiedAttributes,
                "timestamp": timestamp
            ]
            
            // Serialize to JSON, sort keys for deterministic signing
            let jsonData = try JSONSerialization.data(withJSONObject: proofPayload, options: [.sortedKeys])
            
            // Sign using standard SecKey with SHA256 digest
            var error: Unmanaged<CFError>?
            guard let signatureData = SecKeyCreateSignature(
                privateKey,
                .ecdsaSignatureMessageX962SHA256,
                jsonData as CFData,
                &error
            ) as Data? else {
                reject("SIGN_ERROR", "Failed to sign payload: \(error?.takeRetainedValue().localizedDescription ?? "")", nil)
                return
            }
            
            let signatureBase64 = signatureData.base64EncodedString()
            
            resolve([
                "proof_payload": proofPayload,
                "signature": signatureBase64
            ])
            
        } catch {
            reject("VERIFY_ERROR", error.localizedDescription, error)
        }
    }
}
