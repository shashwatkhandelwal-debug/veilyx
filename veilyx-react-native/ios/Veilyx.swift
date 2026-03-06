import Foundation
import CryptoKit
import LocalAuthentication
import UIKit
import UniformTypeIdentifiers

@objc(Veilyx)
class Veilyx: NSObject, UIDocumentPickerDelegate {
    
    private let keyAlias = "veilyx_identity_key"
    private var deviceId: String = ""
    private var pendingPickerResolve: RCTPromiseResolveBlock?
    private var pendingPickerReject: RCTPromiseRejectBlock?
    
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
                    #if targetEnvironment(simulator)
                    reject("INIT_ERROR", "Secure Enclave is not available on iOS Simulator. Please test on a real device.", nil)
                    #else
                    reject("INIT_ERROR", "Could not generate Secure Enclave key: \(error?.takeRetainedValue().localizedDescription ?? "")", nil)
                    #endif
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
    
    @objc(requestProof:withChecks:withNonce:withAadhaar:withResolver:withRejecter:)
    func requestProof(companyName: String, checks: [String], nonce: String, aadhaarXmlData: String, resolve: @escaping RCTPromiseResolveBlock, reject: @escaping RCTPromiseRejectBlock) {
        do {
            guard !deviceId.isEmpty else {
                reject("NOT_INITIALIZED", "SDK not initialized. Call initialize() first.", nil)
                return
            }
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
                "timestamp": timestamp,
                "nonce": nonce
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
    
    @objc(pickAadhaarFile:withRejecter:)
    func pickAadhaarFile(resolve: @escaping RCTPromiseResolveBlock, reject: @escaping RCTPromiseRejectBlock) {
        pendingPickerResolve = resolve
        pendingPickerReject = reject
        
        DispatchQueue.main.async {
            let supportedTypes: [UTType] = [UTType.xml, UTType.data]
            let picker = UIDocumentPickerViewController(forOpeningContentTypes: supportedTypes)
            picker.allowsMultipleSelection = false
            picker.delegate = self
            
            if let viewController = RCTPresentedViewController() {
                viewController.present(picker, animated: true, completion: nil)
            } else {
                self.pendingPickerResolve = nil
                self.pendingPickerReject = nil
                reject("PRESENT_ERROR", "Could not find a view controller to present the picker", nil)
            }
        }
    }
    
    @objc(readAadhaarFile:withResolver:withRejecter:)
    func readAadhaarFile(filePath: String, resolve: @escaping RCTPromiseResolveBlock, reject: @escaping RCTPromiseRejectBlock) {
        do {
            let url = URL(string: filePath) ?? URL(fileURLWithPath: filePath)
            let content = try String(contentsOf: url, encoding: .utf8)
            resolve(content)
        } catch {
            reject("READ_ERROR", error.localizedDescription, error)
        }
    }
    
    // MARK: - UIDocumentPickerDelegate
    
    func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
        guard let url = urls.first else {
            pendingPickerReject?("PICK_ERROR", "No file selected", nil)
            pendingPickerResolve = nil
            pendingPickerReject = nil
            return
        }
        
        let accessing = url.startAccessingSecurityScopedResource()
        do {
            let content = try String(contentsOf: url, encoding: .utf8)
            pendingPickerResolve?(content)
        } catch {
            pendingPickerReject?("READ_ERROR", error.localizedDescription, nil)
        }
        if accessing {
            url.stopAccessingSecurityScopedResource()
        }
        pendingPickerResolve = nil
        pendingPickerReject = nil
    }
    
    func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
        pendingPickerReject?("CANCELLED", "File picker was cancelled", nil)
        pendingPickerResolve = nil
        pendingPickerReject = nil
    }
    
    // MARK: - DigiLocker Deep Link Handling
    
    @objc(handleDeepLink:withResolver:withRejecter:)
    func handleDeepLink(url: String, resolve: @escaping RCTPromiseResolveBlock, reject: @escaping RCTPromiseRejectBlock) {
        guard let components = URLComponents(string: url) else {
            reject("INVALID_LINK", "Could not parse URL", nil)
            return
        }
        
        let queryItems = components.queryItems ?? []
        let code = queryItems.first(where: { $0.name == "code" })?.value
        let state = queryItems.first(where: { $0.name == "state" })?.value
        
        guard let code = code, let state = state else {
            reject("INVALID_LINK", "Missing code or state in callback URL", nil)
            return
        }
        
        resolve([
            "code": code,
            "state": state
        ])
    }
    
    @objc(handleDigiLockerCallback:withState:withResolver:withRejecter:)
    func handleDigiLockerCallback(code: String, state: String, resolve: @escaping RCTPromiseResolveBlock, reject: @escaping RCTPromiseRejectBlock) {
        let backendUrl = Bundle.main.object(forInfoDictionaryKey: "VEILYX_BACKEND_URL") as? String ?? "http://127.0.0.1:8000"
        let urlString = "\(backendUrl)/digilocker/callback?code=\(code)&state=\(state)"
        
        guard let url = URL(string: urlString) else {
            reject("CALLBACK_ERROR", "Invalid callback URL", nil)
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 30.0
        
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                reject("CALLBACK_ERROR", "Network error: \(error.localizedDescription)", error)
                return
            }
            
            guard let data = data else {
                reject("CALLBACK_ERROR", "No data received from server", nil)
                return
            }
            
            do {
                if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let aadhaarXml = json["aadhaar_xml"] as? String {
                    resolve(aadhaarXml)
                } else {
                    reject("CALLBACK_ERROR", "Invalid response format from server", nil)
                }
            } catch {
                reject("CALLBACK_ERROR", "Failed to parse server response: \(error.localizedDescription)", error)
            }
        }
        task.resume()
    }
}
