package com.veilyx

import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.WritableMap
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.ReadableArray
import com.facebook.react.bridge.ActivityEventListener

import com.google.android.play.core.integrity.IntegrityManagerFactory
import com.google.android.play.core.integrity.IntegrityTokenRequest
import com.google.android.gms.tasks.Tasks
import org.xmlpull.v1.XmlPullParserFactory
import org.xmlpull.v1.XmlPullParser
import java.io.StringReader
import java.io.BufferedReader
import java.io.InputStreamReader

import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.spec.ECGenParameterSpec
import java.util.UUID
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.app.Activity
import android.util.Base64
import org.json.JSONObject
import java.security.Signature
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

class VeilyxModule(reactContext: ReactApplicationContext) : ReactContextBaseJavaModule(reactContext), ActivityEventListener {

    private val KEY_ALIAS = "veilyx_identity_key"
    private var deviceId: String = ""
    private var pendingPickerPromise: Promise? = null

    init {
        reactContext.addActivityEventListener(this)
    }

    private fun getOrCreateDeviceId(context: Context): String {
        val prefs = context.getSharedPreferences("VeilyxPrefs", Context.MODE_PRIVATE)
        val existingId = prefs.getString("veilyx_device_id", null)
        if (existingId != null) {
            return existingId
        }
        val newId = UUID.randomUUID().toString()
        prefs.edit().putString("veilyx_device_id", newId).apply()
        return newId
    }

    override fun getName(): String {
        return "Veilyx"
    }

    @ReactMethod
    fun initialize(promise: Promise) {
        try {
            if (deviceId.isEmpty()) {
                deviceId = getOrCreateDeviceId(reactApplicationContext)
            }

            val keyStore = KeyStore.getInstance("AndroidKeyStore")
            keyStore.load(null)

            if (!keyStore.containsAlias(KEY_ALIAS)) {
                val keyPairGenerator = KeyPairGenerator.getInstance(
                    KeyProperties.KEY_ALGORITHM_RSA, "AndroidKeyStore"
                )
                
                val parameterSpec = KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
                )
                .setDigests(KeyProperties.DIGEST_SHA256)
                .setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1)
                .build()

                keyPairGenerator.initialize(parameterSpec)
                keyPairGenerator.generateKeyPair()
            }

            val entry = keyStore.getEntry(KEY_ALIAS, null) as KeyStore.PrivateKeyEntry
            val publicKey = entry.certificate.publicKey
            val publicKeyEncoded = Base64.encodeToString(publicKey.encoded, Base64.NO_WRAP)
            
            // Format to PEM
            val pem = "-----BEGIN PUBLIC KEY-----\n" +
                      publicKeyEncoded.chunked(64).joinToString("\n") +
                      "\n-----END PUBLIC KEY-----"

            val map: WritableMap = Arguments.createMap()
            map.putString("deviceId", deviceId)
            map.putString("publicKeyPem", pem)
            
            var playIntegrityToken = "dummy_android_play_integrity_token"
            try {
                val integrityManager = IntegrityManagerFactory.create(reactApplicationContext)
                val nonceStr = UUID.randomUUID().toString()
                val request = IntegrityTokenRequest.builder().setNonce(nonceStr).build()
                val integrityTokenResponse = Tasks.await(integrityManager.requestIntegrityToken(request))
                playIntegrityToken = integrityTokenResponse.token()
            } catch (e: Exception) {
                playIntegrityToken = "error_fetching_token: " + e.message
            }
            map.putString("attestationPayload", playIntegrityToken)
            
            promise.resolve(map)
        } catch (e: Exception) {
            promise.reject("INIT_ERROR", e.message)
        }
    }

    @ReactMethod
    fun requestProof(companyName: String, checks: ReadableArray, aadhaarXmlData: String, promise: Promise) {
        if (deviceId.isEmpty()) {
            promise.reject("NOT_INITIALIZED", "SDK not initialized. Call initialize() first.")
            return
        }
        try {
            // Simulated local verification logic with actual Aadhaar XML offline parsing check
            val verifiedAttributes = JSONObject()
            for (i in 0 until checks.size()) {
                val check = checks.getString(i)
                if (check == "age_above_18") {
                    var verified = false
                    try {
                        val factory = XmlPullParserFactory.newInstance()
                        val parser = factory.newPullParser()
                        parser.setInput(StringReader(aadhaarXmlData))
                        var eventType = parser.eventType
                        while (eventType != XmlPullParser.END_DOCUMENT) {
                            if (eventType == XmlPullParser.START_TAG && parser.name == "Poi") {
                                val dob = parser.getAttributeValue(null, "dob")
                                if (dob != null) {
                                    val formats = arrayOf(SimpleDateFormat("dd-MM-yyyy", Locale.US), SimpleDateFormat("yyyy-MM-dd", Locale.US))
                                    for (format in formats) {
                                        try {
                                            val dobDate = format.parse(dob)
                                            if (dobDate != null) {
                                                val cal = java.util.Calendar.getInstance()
                                                cal.add(java.util.Calendar.YEAR, -18)
                                                if (dobDate.before(cal.time) || dobDate.equals(cal.time)) {
                                                    verified = true
                                                }
                                            }
                                            break
                                        } catch (e: Exception) {}
                                    }
                                }
                            }
                            eventType = parser.next()
                        }
                    } catch (e: Exception) {
                        // Proceed with verified = false
                    }
                    verifiedAttributes.put(check, verified)
                } else {
                    verifiedAttributes.put(check, true)
                }
            }

            val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSSSS", Locale.US)
            dateFormat.timeZone = TimeZone.getTimeZone("UTC")
            val timestamp = dateFormat.format(Date())

            val proofPayload = JSONObject()
            proofPayload.put("verification_id", UUID.randomUUID().toString())
            proofPayload.put("device_id", deviceId)
            proofPayload.put("requested_by", companyName)
            proofPayload.put("attributes_verified", verifiedAttributes)
            proofPayload.put("timestamp", timestamp)

            // Construct deterministic JSON (keys sorted)
            val sortedKeys = proofPayload.keys().asSequence().sorted().toList()
            fun toSortedJsonString(obj: JSONObject): String {
                val sortedKeysFunc = obj.keys().asSequence().sorted().toList()
                val sb = StringBuilder("{")
                for ((index, key) in sortedKeysFunc.withIndex()) {
                    sb.append(JSONObject.quote(key)).append(":")
                    when (val value = obj.get(key)) {
                        is JSONObject -> sb.append(toSortedJsonString(value))
                        is String -> sb.append(JSONObject.quote(value))
                        is Boolean -> sb.append(value)
                        is Number -> sb.append(value)
                        else -> sb.append(JSONObject.quote(value.toString()))
                    }
                    if (index < sortedKeysFunc.size - 1) sb.append(",")
                }
                sb.append("}")
                return sb.toString()
            }

            // Sign Payload
            val keyStore = KeyStore.getInstance("AndroidKeyStore")
            keyStore.load(null)
            val entry = keyStore.getEntry(KEY_ALIAS, null) as KeyStore.PrivateKeyEntry

            val signature = Signature.getInstance("SHA256withRSA")
            signature.initSign(entry.privateKey)
            signature.update(toSortedJsonString(proofPayload).toByteArray(Charsets.UTF_8))
            val signedBytes = signature.sign()

            val signatureBase64 = Base64.encodeToString(signedBytes, Base64.NO_WRAP)

            // WritableMap doesn't support nested objects easily, so return stringified or custom construct
            val result: WritableMap = Arguments.createMap()
            
            val payloadMap: WritableMap = Arguments.createMap()
            payloadMap.putString("verification_id", proofPayload.getString("verification_id"))
            payloadMap.putString("device_id", proofPayload.getString("device_id"))
            payloadMap.putString("requested_by", proofPayload.getString("requested_by"))
            payloadMap.putString("timestamp", proofPayload.getString("timestamp"))
            
            val attrMap: WritableMap = Arguments.createMap()
            for (i in 0 until checks.size()) {
                val check = checks.getString(i)
                attrMap.putBoolean(check, verifiedAttributes.optBoolean(check, false))
            }
            payloadMap.putMap("attributes_verified", attrMap)
            
            result.putMap("proof_payload", payloadMap)
            result.putString("signature", signatureBase64)

            promise.resolve(result)
            
        } catch (e: Exception) {
            promise.reject("VERIFY_ERROR", e.message)
        }
    }

    @ReactMethod
    fun pickAadhaarFile(promise: Promise) {
        try {
            val activity = currentActivity
            if (activity == null) {
                promise.reject("ACTIVITY_ERROR", "No current activity found")
                return
            }
            pendingPickerPromise = promise
            val intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.type = "*/*"
            intent.putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("text/xml", "application/xml"))
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            activity.startActivityForResult(Intent.createChooser(intent, "Select Aadhaar XML File"), 1001)
        } catch (e: Exception) {
            pendingPickerPromise = null
            promise.reject("PICK_ERROR", e.message)
        }
    }

    override fun onActivityResult(activity: Activity?, requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode == 1001) {
            if (resultCode == Activity.RESULT_OK && data != null && data.data != null) {
                pendingPickerPromise?.resolve(data.data.toString())
            } else {
                pendingPickerPromise?.reject("CANCELLED", "File picker was cancelled")
            }
            pendingPickerPromise = null
        }
    }

    override fun onNewIntent(intent: Intent?) {
        // No-op, required by ActivityEventListener interface
    }

    @ReactMethod
    fun readAadhaarFile(fileUri: String, promise: Promise) {
        try {
            val uri = Uri.parse(fileUri)
            val inputStream = reactApplicationContext.contentResolver.openInputStream(uri)
            if (inputStream == null) {
                promise.reject("READ_ERROR", "Could not open file")
                return
            }
            val reader = BufferedReader(InputStreamReader(inputStream))
            val content = reader.readText()
            reader.close()
            inputStream.close()
            promise.resolve(content)
        } catch (e: Exception) {
            promise.reject("READ_ERROR", e.message)
        }
    }

    @ReactMethod
    fun handleDigiLockerCallback(code: String, state: String, promise: Promise) {
        Thread {
            try {
                val url = java.net.URL("http://10.0.2.2:8000/digilocker/callback?code=$code&state=$state")
                val connection = url.openConnection() as java.net.HttpURLConnection
                connection.requestMethod = "GET"
                connection.connectTimeout = 30000
                connection.readTimeout = 30000
                
                val responseCode = connection.responseCode
                if (responseCode != 200) {
                    promise.reject("CALLBACK_ERROR", "Server returned $responseCode")
                    return@Thread
                }
                
                val response = connection.inputStream.bufferedReader().readText()
                val json = JSONObject(response)
                val aadhaarXml = json.getString("aadhaar_xml")
                promise.resolve(aadhaarXml)
            } catch (e: Exception) {
                promise.reject("CALLBACK_ERROR", e.message)
            }
        }.start()
    }
}
