import { NativeModules, Platform } from 'react-native';

const LINKING_ERROR =
  `The package 'veilyx-react-native' doesn't seem to be linked. Make sure: \n\n` +
  Platform.select({ ios: "- You have run 'pod install'\n", default: '' }) +
  '- You rebuilt the app after installing the package\n' +
  '- You are not using Expo Go\n';

const Veilyx = NativeModules.Veilyx
  ? NativeModules.Veilyx
  : new Proxy(
    {},
    {
      get() {
        throw new Error(LINKING_ERROR);
      },
    }
  );

export type VerificationCheck = 'age_above_18' | 'name_match' | 'document_valid';

export interface ProofRequest {
  companyName: string;
  checks: VerificationCheck[];
  aadhaarXml?: string;
}

export interface VeilyxProof {
  verification_id: string;
  device_id: string;
  requested_by: string;
  attributes_verified: Record<string, boolean>;
  timestamp: string;
}

export interface SignedProof {
  proof_payload: VeilyxProof;
  signature: string;
}

const initialize = (): Promise<{ deviceId: string; publicKeyPem: string; attestationPayload: string }> => {
  return Veilyx.initialize();
};

const requestProof = (request: ProofRequest): Promise<SignedProof> => {
  return Veilyx.requestProof(request.companyName, request.checks, request.aadhaarXml || "");
};

/**
 * Opens the native file picker for the user to select an Aadhaar XML file.
 * On Android, launches ACTION_GET_CONTENT with XML mime types.
 * On iOS, presents a UIDocumentPickerViewController for XML files.
 * @returns The XML file contents as a string.
 */
const pickAadhaarFile = (): Promise<string> => {
  return Veilyx.pickAadhaarFile();
};

/**
 * Reads an Aadhaar XML file from a known file path and returns its contents.
 * Use this when the file URI is already available (e.g., from a previous picker result on Android).
 * @param filePath - The absolute file path or content URI to read from.
 * @returns The XML file contents as a string.
 */
const readAadhaarFile = (filePath: string): Promise<string> => {
  return Veilyx.readAadhaarFile(filePath);
};

/**
 * Call this from your app's deep link handler when DigiLocker redirects back.
 * Parses the callback URL and extracts the OAuth code and state parameters.
 * @param url - The full callback URL from DigiLocker redirect.
 * @returns An object containing the authorization code and state.
 */
const handleDeepLink = (url: string): Promise<{ code: string, state: string }> => {
  return Veilyx.handleDeepLink(url);
};

/**
 * Exchanges the OAuth authorization code for Aadhaar XML via Veilyx backend.
 * Call this after receiving code and state from handleDeepLink.
 * @param code - The OAuth authorization code from DigiLocker.
 * @param state - The OAuth state parameter for CSRF validation.
 * @returns The Aadhaar XML content as a string.
 */
const handleDigiLockerCallback = (code: string, state: string): Promise<string> => {
  return Veilyx.handleDigiLockerCallback(code, state);
};

export default {
  initialize,
  requestProof,
  pickAadhaarFile,
  readAadhaarFile,
  handleDeepLink,
  handleDigiLockerCallback
};
