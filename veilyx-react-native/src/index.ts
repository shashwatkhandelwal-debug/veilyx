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

export function initialize(): Promise<{ deviceId: string; publicKeyPem: string; attestationPayload: string }> {
  return Veilyx.initialize();
}

export function requestProof(request: ProofRequest): Promise<SignedProof> {
  return Veilyx.requestProof(request.companyName, request.checks);
}

export default {
  initialize,
  requestProof
};
