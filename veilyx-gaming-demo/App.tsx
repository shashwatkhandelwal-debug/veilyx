import React, { useState, useEffect } from 'react';
import {
    SafeAreaView,
    StyleSheet,
    Text,
    View,
    TouchableOpacity,
    ActivityIndicator,
    Alert,
    ScrollView,
    Linking
} from 'react-native';

// Import the local SDK
import VeilyxSDK from 'veilyx-react-native';

const VEILYX_API_KEY = process.env.VEILYX_API_KEY || 'YOUR_API_KEY_HERE';

const IntegratorDemoApp = () => {
    const BACKEND_URL = 'https://YOUR-RAILWAY-URL.railway.app';
    const [isInitializing, setIsInitializing] = useState(false);
    const [deviceReg, setDeviceReg] = useState<any>(null);
    const [isVerifying, setIsVerifying] = useState(false);
    const [proofResult, setProofResult] = useState<any>(null);
    const [backendVerification, setBackendVerification] = useState<any>(null);
    const [isDigiLockerLoading, setIsDigiLockerLoading] = useState(false);

    const fetchNonce = async (): Promise<string> => {
        const response = await fetch(`${BACKEND_URL}/nonce`, {
            headers: { 'X-API-Key': VEILYX_API_KEY }
        });
        if (!response.ok) throw new Error("Failed to fetch security nonce");
        const { nonce } = await response.json();
        return nonce;
    };

    useEffect(() => {
        const handleDeepLinkCallback = async (event: { url: string }) => {
            if (event.url.startsWith('veilyx://digilocker/callback')) {
                try {
                    const parsed = await VeilyxSDK.handleDeepLink(event.url);
                    const aadhaarXml = await VeilyxSDK.handleDigiLockerCallback(parsed.code, parsed.state);
                    const nonce = await fetchNonce();
                    const proof = await VeilyxSDK.requestProof({
                        companyName: 'RummyKing Pro',
                        checks: ['age_above_18'],
                        nonce: nonce,
                        aadhaarXml: aadhaarXml
                    });
                    setProofResult(proof);
                    await simulateBackendVerification(proof);
                } catch (e: any) {
                    Alert.alert('DigiLocker Callback Error', e.message);
                }
            }
        };

        const subscription = Linking.addEventListener('url', handleDeepLinkCallback);
        return () => subscription.remove();
    }, []);


    const simulateBackendVerification = async (proof: any) => {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);
            const response = await fetch(`${BACKEND_URL}/verify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': VEILYX_API_KEY
                },
                body: JSON.stringify({
                    proof_payload: proof.proof_payload,
                    signature: proof.signature
                }),
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`Backend verification failed with status ${response.status}`);
            }

            const data = await response.json();

            if (data.valid) {
                setBackendVerification({
                    status: "SUCCESS",
                    message: data.message,
                    action: "UNLOCK_GAME"
                });
                Alert.alert("Matched!", "Proof cryptography verified successfully by backend.");
            } else {
                setBackendVerification({
                    status: "FAILED",
                    message: data.message,
                    action: "LOCK_GAME"
                });
                Alert.alert("Verification Failed", data.message);
            }
        } catch (e: any) {
            console.error("Backend Error:", e);
            Alert.alert("Backend Offline", "Could not connect to verification server. " + e.message);
        }
    };



    const handleOpenUIDAI = () => {
        Linking.openURL('https://myaadhaar.uidai.gov.in/offline-ekyc');
    };

    const handleDigiLockerVerify = async () => {
        if (!deviceReg) {
            Alert.alert('Error', 'Please initialize the SDK first');
            return;
        }
        try {
            setIsDigiLockerLoading(true);
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);
            const response = await fetch(`${BACKEND_URL}/digilocker/auth`, { signal: controller.signal });
            clearTimeout(timeoutId);
            const data = await response.json();
            await Linking.openURL(data.auth_url);
        } catch (e: any) {
            Alert.alert('DigiLocker Error', e.message);
        } finally {
            setIsDigiLockerLoading(false);
        }
    };

    const handleSimulateAppStart = async () => {
        try {
            setIsInitializing(true);
            const initResult = await VeilyxSDK.initialize();
            setDeviceReg(initResult);
            Alert.alert("Success", "SDK Initialized & Device Registered securely.");
        } catch (e: any) {
            console.error(e);
            Alert.alert("Init Error", e.message);
        } finally {
            setIsInitializing(false);
        }
    };

    const handlePlayGame = async () => {
        if (!deviceReg) {
            Alert.alert("Error", "Please initialize the SDK first");
            return;
        }

        try {
            setIsVerifying(true);

            let aadhaarXml: string;
            try {
                const fileUri = await VeilyxSDK.pickAadhaarFile();
                aadhaarXml = await VeilyxSDK.readAadhaarFile(fileUri);
            } catch (pickError: any) {
                Alert.alert('Verification cancelled', 'Verification cancelled — Aadhaar file required.');
                setIsVerifying(false);
                return;
            }

            const nonce = await fetchNonce();
            const proof = await VeilyxSDK.requestProof({
                companyName: 'RummyKing Pro',
                checks: ['age_above_18'],
                nonce: nonce,
                aadhaarXml: aadhaarXml
            });

            setProofResult(proof);
            await simulateBackendVerification(proof);

        } catch (e: any) {
            console.error(e);
            Alert.alert("Verification Error", e.message);
        } finally {
            setIsVerifying(false);
        }
    };

    return (
        <SafeAreaView style={styles.container}>
            <ScrollView contentContainerStyle={styles.scroll}>

                <View style={styles.header}>
                    <Text style={styles.title}>RummyKing Pro ♠️</Text>
                    <Text style={styles.subtitle}>Real Money Gaming App</Text>
                </View>

                <View style={styles.card}>
                    <Text style={styles.cardTitle}>1. System Initialization</Text>
                    <Text style={styles.cardDesc}>
                        On app launch, we initialize Veilyx. It generates a hardware-backed RSA key and attests the device.
                    </Text>

                    <TouchableOpacity
                        style={styles.buttonSecondary}
                        onPress={handleSimulateAppStart}
                        disabled={isInitializing}
                    >
                        {isInitializing ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Initialize Veilyx SDK</Text>}
                    </TouchableOpacity>

                    {deviceReg && (
                        <View style={styles.codeBlock}>
                            <Text style={styles.codeText}>Device ID: {deviceReg.deviceId}</Text>
                            <Text style={styles.codeText}>Public Key: ...{deviceReg.publicKeyPem.substring(27, 47)}...</Text>
                        </View>
                    )}
                </View>

                <View style={[styles.card, !deviceReg && styles.disabledCard]}>
                    <Text style={styles.cardTitle}>1.5. Aadhaar XML Selection</Text>
                    <Text style={styles.cardDesc}>
                        User selects their Aadhaar Offline XML from their device. The file never leaves the device — it is read locally by the Veilyx SDK.
                    </Text>

                    {deviceReg && (
                        <TouchableOpacity
                            style={[styles.buttonSecondary, { backgroundColor: '#FF6B00' }]}
                            onPress={handleOpenUIDAI}
                        >
                            <Text style={styles.buttonText}>Download Aadhaar XML from UIDAI</Text>
                        </TouchableOpacity>
                    )}

                    {deviceReg && (
                        <Text style={{ color: '#666', fontSize: 12, marginTop: 10, lineHeight: 18 }}>
                            Step 1: Download your Aadhaar Offline XML from UIDAI portal, then come back and tap 'Join Cash Table'
                        </Text>
                    )}

                    {deviceReg && (
                        <Text style={{ color: '#999', fontSize: 12, marginTop: 15, marginBottom: 15, textAlign: 'center' }}>
                            ── OR ──
                        </Text>
                    )}

                    {deviceReg && (
                        <TouchableOpacity
                            style={[styles.buttonSecondary, { backgroundColor: '#FF6B00' }]}
                            onPress={handleDigiLockerVerify}
                            disabled={isDigiLockerLoading}
                        >
                            {isDigiLockerLoading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Connect via DigiLocker (1-tap)</Text>}
                        </TouchableOpacity>
                    )}

                    {deviceReg && (
                        <Text style={{ color: '#666', fontSize: 12, marginTop: 10, lineHeight: 18 }}>
                            Faster: DigiLocker fetches your Aadhaar XML automatically with your consent
                        </Text>
                    )}

                    {!deviceReg && <Text style={{ color: '#999', fontSize: 12, marginTop: 5 }}>⚠️ Initialize SDK first</Text>}
                </View>

                <View style={[styles.card, !deviceReg && styles.disabledCard]}>
                    <Text style={styles.cardTitle}>2. Age Verification Flow</Text>
                    <Text style={styles.cardDesc}>
                        User clicks 'Play Cash Game'. To comply with regulations, we must prove they are 18+ without storing their ID.
                    </Text>

                    <TouchableOpacity
                        style={[styles.buttonPrimary, !deviceReg && styles.disabledButton]}
                        onPress={handlePlayGame}
                        disabled={!deviceReg || isVerifying}
                    >
                        {isVerifying ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Join Cash Table ($50)</Text>}
                    </TouchableOpacity>
                </View>

                {proofResult && (
                    <View style={styles.card}>
                        <Text style={styles.cardTitle}>3. Local Proof Generated</Text>
                        <Text style={styles.cardDesc}>
                            The SDK processed the user locally and signed this payload using the physical device Secure Enclave.
                        </Text>
                        <View style={styles.codeBlock}>
                            <Text style={styles.codeText}>{JSON.stringify(proofResult.proof_payload, null, 2)}</Text>
                            <Text style={styles.codeText} numberOfLines={2}>Sig: {proofResult.signature}</Text>
                        </View>
                    </View>
                )}

                {backendVerification && (
                    <View style={[styles.card, { borderColor: '#4caf50', borderWidth: 2 }]}>
                        <Text style={styles.cardTitle}>4. Backend Verification 🌍</Text>
                        <Text style={styles.cardDesc}>
                            Server mathematically verified the signature against the public key.
                        </Text>
                        <View style={styles.codeBlock}>
                            <Text style={[styles.codeText, { color: '#4caf50', fontWeight: 'bold' }]}>
                                {backendVerification.action}: {backendVerification.message}
                            </Text>
                        </View>
                    </View>
                )}

            </ScrollView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#f0f2f5' },
    scroll: { padding: 20 },
    header: { alignItems: 'center', marginBottom: 30, marginTop: 20 },
    title: { fontSize: 28, fontWeight: 'bold', color: '#1a1a1a' },
    subtitle: { fontSize: 16, color: '#666', marginTop: 5 },
    card: { backgroundColor: '#fff', padding: 20, borderRadius: 12, marginBottom: 20, shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 10, elevation: 3 },
    disabledCard: { opacity: 0.6 },
    cardTitle: { fontSize: 18, fontWeight: '600', color: '#333', marginBottom: 8 },
    cardDesc: { fontSize: 14, color: '#666', marginBottom: 15, lineHeight: 20 },
    buttonPrimary: { backgroundColor: '#2196F3', padding: 15, borderRadius: 8, alignItems: 'center' },
    buttonSecondary: { backgroundColor: '#757575', padding: 15, borderRadius: 8, alignItems: 'center' },
    disabledButton: { backgroundColor: '#cccccc' },
    buttonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
    codeBlock: { backgroundColor: '#1e1e1e', padding: 12, borderRadius: 6, marginTop: 15 },
    codeText: { color: '#a6e22e', fontFamily: 'monospace', fontSize: 12 }
});

export default IntegratorDemoApp;