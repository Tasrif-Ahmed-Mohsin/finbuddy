/**
 * Passkey signing: the person's device signs the exact payment (its hash) and the server checks the signature
 * before the approval counts (backend/app/security/passkey.py).
 *
 * - Web: a real passkey through WebAuthn (Windows Hello, Touch ID, Android screen lock). If the browser cannot make
 *   one, a sandbox "browser demo key" is offered instead and is labelled as such on every approval.
 * - Phone app: a P-256 key made on this phone the first time, kept in secure storage (Android Keystore encrypted)
 *   and used only after the fingerprint, face or PIN check. It signs the same WebAuthn format.
 *
 * No private key is in the code or on the server; the server only ever gets the public key.
 */
import { p256 } from '@noble/curves/nist.js';
import { sha256 } from '@noble/hashes/sha2.js';
import { getRandomBytes } from 'expo-crypto';
import * as LocalAuthentication from 'expo-local-authentication';
import * as SecureStore from 'expo-secure-store';
import { Alert, Platform } from 'react-native';

import { post, type Role } from './api';

export type PasskeyAssertion = {
  credential_id: string;
  client_data_json: string;
  authenticator_data: string;
  signature: string;
};

type Kind = 'webauthn' | 'device_key';
type Stored = { credentialId: string; kind: Kind; publicKey: string; label: string; secret?: string; counter: number };
type Call = <T>(path: string, init?: RequestInit) => Promise<T>;

const APP_ORIGIN = 'sathi-app://device';
const APP_RP_ID = 'sathi.app';
const enc = new TextEncoder();

// ---- bytes ------------------------------------------------------------------
function b64(bytes: Uint8Array): string {
  let s = '';
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s);
}
const b64url = (bytes: Uint8Array) => b64(bytes).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
function fromB64url(s: string): Uint8Array {
  const t = s.replace(/-/g, '+').replace(/_/g, '/');
  const bin = atob(t + '='.repeat((4 - (t.length % 4)) % 4));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}
function hexToBytes(hex: string): Uint8Array {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  return out;
}
const toHex = (bytes: Uint8Array) => Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
function concat(...parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) {
    out.set(p, at);
    at += p.length;
  }
  return out;
}
const bufBytes = (b: ArrayBuffer | ArrayBufferView) =>
  b instanceof ArrayBuffer ? new Uint8Array(b) : new Uint8Array(b.buffer, b.byteOffset, b.byteLength);

// ---- where the key lives ---------------------------------------------------------
const isWeb = Platform.OS === 'web';
const storeKey = (role: Role) => (isWeb ? `sathi.passkey.${role}.${globalThis.location?.hostname ?? 'web'}` : `sathi.passkey.${role}`);

async function load(role: Role): Promise<Stored | null> {
  try {
    const raw = isWeb ? globalThis.localStorage?.getItem(storeKey(role)) : await SecureStore.getItemAsync(storeKey(role));
    return raw ? (JSON.parse(raw) as Stored) : null;
  } catch {
    return null;
  }
}

async function save(role: Role, s: Stored): Promise<void> {
  const raw = JSON.stringify(s);
  if (isWeb) globalThis.localStorage?.setItem(storeKey(role), raw);
  else await SecureStore.setItemAsync(storeKey(role), raw, { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY });
}

// ---- WebAuthn (web) -----------------------------------------------------------------
type WebAuthnNav = {
  credentials?: {
    create(o: unknown): Promise<{ rawId: ArrayBuffer; response: { getPublicKey?: () => ArrayBuffer | null; getPublicKeyAlgorithm?: () => number } } | null>;
    get(o: unknown): Promise<{ response: { clientDataJSON: ArrayBuffer; authenticatorData: ArrayBuffer; signature: ArrayBuffer } } | null>;
  };
};
const webAuthn = () =>
  isWeb && typeof globalThis.PublicKeyCredential !== 'undefined' && globalThis.isSecureContext
    ? (globalThis.navigator as unknown as WebAuthnNav).credentials
    : undefined;

async function createWebAuthn(role: Role): Promise<Stored | null> {
  const creds = webAuthn();
  if (!creds) return null;
  const cred = await creds.create({
    publicKey: {
      challenge: getRandomBytes(32),
      rp: { name: 'Sathi', id: globalThis.location.hostname },
      user: { id: enc.encode(`sathi-${role}`), name: `${role}@sathi`, displayName: role === 'parent' ? 'Sathi · parent' : 'Sathi · student' },
      pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
      authenticatorSelection: { userVerification: 'required', residentKey: 'preferred' },
      attestation: 'none',
      timeout: 60000,
    },
  });
  const spki = cred?.response.getPublicKey?.();
  if (!cred || !spki || cred.response.getPublicKeyAlgorithm?.() !== -7) return null;
  return { credentialId: b64url(bufBytes(cred.rawId)), kind: 'webauthn', publicKey: b64(bufBytes(spki)), label: 'This browser’s passkey', counter: 0 };
}

async function signWebAuthn(s: Stored, hashHex: string): Promise<PasskeyAssertion | null> {
  const got = await webAuthn()!.get({
    publicKey: {
      challenge: hexToBytes(hashHex),
      rpId: globalThis.location.hostname,
      allowCredentials: [{ type: 'public-key', id: fromB64url(s.credentialId) }],
      userVerification: 'required',
      timeout: 60000,
    },
  });
  if (!got) return null;
  return {
    credential_id: s.credentialId,
    client_data_json: b64url(bufBytes(got.response.clientDataJSON)),
    authenticator_data: b64url(bufBytes(got.response.authenticatorData)),
    signature: b64url(bufBytes(got.response.signature)),
  };
}

// ---- the device key (phone app; browser demo key) ----------------------------------------
function createDeviceKey(label: string): Stored {
  const secret = p256.utils.randomSecretKey(getRandomBytes(48));
  return {
    credentialId: `dev-${b64url(getRandomBytes(12))}`,
    kind: 'device_key',
    publicKey: b64(p256.getPublicKey(secret, false)),
    label,
    secret: toHex(secret),
    counter: 0,
  };
}

/** Fingerprint, face or device PIN on the phone; a clear confirmation on the web demo key. Returns whether the
 * person was really verified (the UV flag): only then can the server accept the signature. */
async function verifyPerson(prompt: string): Promise<{ ok: boolean; uv: boolean }> {
  if (isWeb) {
    const ok = typeof globalThis.confirm === 'function' ? globalThis.confirm(`${prompt}\n\nSandbox demo key: confirm to sign.`) : true;
    return { ok, uv: ok };
  }
  if (await LocalAuthentication.hasHardwareAsync()) {
    const r = await LocalAuthentication.authenticateAsync({ promptMessage: prompt, cancelLabel: 'Cancel' });
    if (r.success) return { ok: true, uv: true };
    if (r.error === 'user_cancel' || r.error === 'system_cancel' || r.error === 'app_cancel') return { ok: false, uv: false };
  }
  return new Promise((resolve) =>
    Alert.alert('Sathi', `${prompt}\n\nThis phone has no fingerprint, face or PIN set up, so it cannot sign payments.`, [
      { text: 'OK', onPress: () => resolve({ ok: false, uv: false }) },
    ]),
  );
}

function signDeviceKey(s: Stored, hashHex: string, uv: boolean): PasskeyAssertion {
  const origin = isWeb ? globalThis.location.origin : APP_ORIGIN;
  const rpId = isWeb ? globalThis.location.hostname : APP_RP_ID;
  const clientData = enc.encode(JSON.stringify({ type: 'webauthn.get', challenge: b64url(hexToBytes(hashHex)), origin, crossOrigin: false }));
  const counter = new Uint8Array(4);
  new DataView(counter.buffer).setUint32(0, s.counter, false);
  const authData = concat(sha256(enc.encode(rpId)), Uint8Array.of(0x01 | (uv ? 0x04 : 0)), counter);
  // ECDSA P-256 over authenticatorData || SHA-256(clientDataJSON), deterministic nonce (RFC 6979)
  const signature = p256.sign(concat(authData, sha256(clientData)), hexToBytes(s.secret!), { prehash: true });
  return { credential_id: s.credentialId, client_data_json: b64url(clientData), authenticator_data: b64url(authData), signature: b64url(signature) };
}

// ---- the one entry point ----------------------------------------------------------------
/** This device's passkey for `role`: made the first time (web passkey, else a device key), and registered with the
 * server (again after a server restart, the device keeps its key). */
async function ensurePasskey(role: Role, call: Call): Promise<Stored> {
  let s = await load(role);
  if (!s) {
    if (isWeb) {
      try {
        s = await createWebAuthn(role);
      } catch (e) {
        if (e instanceof Error && e.name === 'NotAllowedError') throw new Error('cancelled');
        s = null;
      }
      s = s ?? createDeviceKey('This browser – demo key (no fingerprint)');
    } else {
      s = createDeviceKey(Platform.OS === 'android' ? 'This phone (fingerprint / PIN)' : 'This phone (Face ID / passcode)');
    }
    await save(role, s);
  }
  const mine = await call<{ credentials: { credential_id: string }[] }>('/auth/passkey/credentials');
  if (!mine.credentials.some((c) => c.credential_id === s!.credentialId)) {
    await call('/auth/passkey/register', post({ credential_id: s.credentialId, public_key: s.publicKey, label: s.label, kind: s.kind }));
  }
  return s;
}

/**
 * Sign `hashHex` (a draft, a mandate proposal or a bank consent) with this device's passkey after the person is
 * verified. Returns null when the person cancels.
 */
export async function signWithPasskey(role: Role, hashHex: string, prompt: string, call: Call): Promise<PasskeyAssertion | null> {
  let s: Stored;
  try {
    s = await ensurePasskey(role, call);
  } catch (e) {
    if (e instanceof Error && e.message === 'cancelled') return null;
    throw e;
  }
  if (s.kind === 'webauthn') {
    try {
      return await signWebAuthn(s, hashHex);
    } catch (e) {
      if (e instanceof Error && e.name === 'NotAllowedError') return null;
      throw e;
    }
  }
  const { ok, uv } = await verifyPerson(prompt);
  if (!ok) return null;
  s = { ...s, counter: s.counter + 1 };
  await save(role, s);
  return signDeviceKey(s, hashHex, uv);
}

/** A fresh Idempotency-Key for one tap on "Send": a retry of the same tap reuses it, so money moves once. */
export function idempotencyKey(): string {
  return `tap-${toHex(getRandomBytes(12))}`;
}
