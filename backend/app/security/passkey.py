"""Passkey approvals: the person's device signs the exact payment (or mandate) before the server lets it count.

The format is a WebAuthn assertion (W3C WebAuthn Level 2, the FIDO2 standard behind passkeys), algorithm ES256
(ECDSA P-256 with SHA-256). The challenge is the draft's hash, so the signature covers exactly the payment shown on
screen ("what you see is what you sign", PSD2 dynamic linking). Before an approval counts, the server checks:

1. the credential is registered to that person (parent or student);
2. clientDataJSON says type "webauthn.get", comes from an allowed origin, and its challenge is the draft hash;
3. authenticatorData is for the expected relying party (rpIdHash) and has User Present and User Verified set
   (UV = fingerprint, face or device PIN, not just a tap);
4. the ECDSA signature over authenticatorData + SHA-256(clientDataJSON) verifies with the registered public key;
5. the same signature has not been used before, and a non-zero sign counter only goes up (a cloned key shows).

Where the keys come from:
* Web: a real platform passkey (Windows Hello, Touch ID, Android screen lock) through navigator.credentials.
* Phone app: a P-256 key made on the phone the first time, kept in the phone's secure storage (Android Keystore
  encrypted), and used only after the fingerprint or PIN check. It signs the same WebAuthn format.
No private key is ever in the source code or on the server. SimulatedAuthenticator (below) makes a fresh random key
for tests, judge runs and the fuzzer only.

Sandbox limits (in the known-risk list): registering a device needs only the person's login here; a bank would add
identity proofing before enrolling a new device. Attestation is not checked (attestation "none", like most passkey
sites), so the server cannot prove the key is in hardware, only that the person's registered device signed.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

APP_ORIGIN = "sathi-app://device"  # the phone app's own origin; its rpId is APP_RP_ID
APP_RP_ID = "sathi.app"
DEFAULT_ORIGINS = (APP_ORIGIN, "http://localhost:8081", "http://localhost:8082", "http://127.0.0.1:8081",
                   "http://localhost:8000", "http://127.0.0.1:8000")
MAX_KEYS_PER_PERSON = 5


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def decode_b64(val: str) -> bytes:
    """Standard base64 or base64url, with or without padding."""
    clean = (val or "").strip().replace("-", "+").replace("_", "/")
    return base64.b64decode(clean + "=" * (-len(clean) % 4), validate=True)


def challenge_for(hash_hex: str) -> str:
    """The WebAuthn challenge for a draft or mandate hash: the hash's 32 bytes, base64url (as clientDataJSON has it)."""
    return b64url(bytes.fromhex(hash_hex))


def load_public_key(public_key: str) -> ec.EllipticCurvePublicKey:
    """A P-256 public key from PEM, base64 SPKI DER (WebAuthn getPublicKey()) or base64 raw point (0x04 || X || Y)."""
    text = (public_key or "").strip()
    if text.startswith("-----BEGIN"):
        key = serialization.load_pem_public_key(text.encode("ascii"))
    else:
        raw = decode_b64(text)
        if len(raw) == 65 and raw[0] == 4:
            key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)
        else:
            key = serialization.load_der_public_key(raw)
    if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
        raise ValueError("only ES256 (ECDSA P-256) passkeys are supported")
    return key


def thumbprint(key: ec.EllipticCurvePublicKey) -> str:
    der = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return "key_" + hashlib.sha256(der).hexdigest()[:12]


def rp_id_for(origin: str) -> str:
    return APP_RP_ID if origin == APP_ORIGIN else (urlparse(origin).hostname or "")


@dataclass
class PasskeyCredential:
    credential_id: str
    actor: str  # "student" | "parent"
    public_key: ec.EllipticCurvePublicKey
    label: str
    kind: str  # "webauthn" (browser/platform passkey) | "device_key" (the phone app's key) | "simulated"
    registered_at: str
    sign_count: int = 0

    @property
    def thumbprint(self) -> str:
        return thumbprint(self.public_key)

    def to_dict(self) -> dict[str, Any]:
        return {"credential_id": self.credential_id, "actor": self.actor, "label": self.label, "kind": self.kind,
                "thumbprint": self.thumbprint, "sign_count": self.sign_count, "registered_at": self.registered_at}


@dataclass
class PasskeyApprovalRecord:
    actor: str
    credential_id: str
    label: str
    kind: str
    thumbprint: str
    draft_hash: str
    origin: str
    verified_at: str
    biometric_uv: bool = True
    alg: str = "ES256"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PasskeyService:
    """Registered passkeys per person, and the check of a signed approval."""

    def __init__(self, origins: tuple[str, ...] | list[str] = DEFAULT_ORIGINS):
        self.origins = set(origins)
        self.credentials: dict[str, list[PasskeyCredential]] = {}
        self._used_signatures: set[str] = set()

    def list_credentials(self, actor: str) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self.credentials.get(actor, [])]

    def register(self, actor: str, credential_id: str, public_key: str, label: str, kind: str, now: datetime) -> PasskeyCredential:
        if actor not in ("student", "parent"):
            raise PermissionError("only the student or the parent can register a passkey")
        if kind not in ("webauthn", "device_key", "simulated"):
            raise ValueError("unknown passkey kind")
        try:
            key = load_public_key(public_key)
        except Exception as e:  # noqa: BLE001 - any parse failure is the same answer to the caller
            raise ValueError(f"not a valid ES256 public key ({e})") from None
        creds = self.credentials.setdefault(actor, [])
        for c in creds:
            if c.credential_id == credential_id:
                if c.thumbprint != thumbprint(key):
                    raise PermissionError("this credential id is already registered with a different key")
                return c  # the same device registering again (for example after the server restarted)
        if len(creds) >= MAX_KEYS_PER_PERSON:
            raise ValueError(f"at most {MAX_KEYS_PER_PERSON} passkeys per person; remove one first")
        cred = PasskeyCredential(credential_id, actor, key, label[:80], kind, now.isoformat(timespec="seconds"))
        creds.append(cred)
        return cred

    def remove(self, actor: str, credential_id: str) -> bool:
        creds = self.credentials.get(actor, [])
        keep = [c for c in creds if c.credential_id != credential_id]
        self.credentials[actor] = keep
        return len(keep) != len(creds)

    def verify_assertion(self, actor: str, expected_hash: str, assertion: dict, now: datetime,
                         extra_origins: tuple[str, ...] = ()) -> tuple[bool, str, PasskeyApprovalRecord | None]:
        """Check one signed approval of `expected_hash` by `actor`. Returns (ok, reason, record)."""
        cred_id = str(assertion.get("credential_id") or "")
        cred = next((c for c in self.credentials.get(actor, []) if c.credential_id == cred_id), None)
        if cred is None:
            return False, f"no passkey '{cred_id[:24]}' is registered for the {actor}", None
        try:
            client_raw = decode_b64(str(assertion.get("client_data_json") or ""))
            client = json.loads(client_raw.decode("utf-8"))
            auth = decode_b64(str(assertion.get("authenticator_data") or ""))
            sig = decode_b64(str(assertion.get("signature") or ""))
        except Exception:  # noqa: BLE001
            return False, "the signed approval is not well-formed", None
        if not isinstance(client, dict) or client.get("type") != "webauthn.get":
            return False, "not a WebAuthn signing response", None
        if client.get("challenge") != challenge_for(expected_hash):
            return False, "the signature is for a different payment (challenge is not this draft's hash)", None
        origin = str(client.get("origin") or "")
        if origin not in self.origins and origin not in extra_origins:
            return False, f"signed on an origin this server does not trust ({origin[:60]})", None
        if len(auth) < 37 or auth[:32] != hashlib.sha256(rp_id_for(origin).encode()).digest():
            return False, "the signature is for a different site (rpIdHash mismatch)", None
        flags = auth[32]
        if not flags & 0x01:
            return False, "user presence (UP) was not confirmed on the device", None
        if not flags & 0x04:
            return False, "the device did not verify the person (UV): fingerprint, face or PIN is required", None
        fingerprint = hashlib.sha256(sig).hexdigest()
        if fingerprint in self._used_signatures:
            return False, "this signature was already used once", None
        counter = int.from_bytes(auth[33:37], "big")
        if counter and counter <= cred.sign_count:
            return False, "the signature counter went backwards: this key may be cloned", None
        if len(sig) == 64:  # raw r || s (noble, WebCrypto) → DER for the verifier
            sig = encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big"))
        try:
            cred.public_key.verify(sig, auth + hashlib.sha256(client_raw).digest(), ec.ECDSA(hashes.SHA256()))
        except (InvalidSignature, ValueError):
            return False, "the signature does not verify with the registered passkey", None
        cred.sign_count = max(cred.sign_count, counter)
        self._used_signatures.add(fingerprint)
        return True, "passkey signature verified", PasskeyApprovalRecord(
            actor=actor, credential_id=cred.credential_id, label=cred.label, kind=cred.kind, thumbprint=cred.thumbprint,
            draft_hash=expected_hash, origin=origin, verified_at=now.isoformat(timespec="seconds"))


class SimulatedAuthenticator:
    """A stand-in device for tests, judge runs and the fuzzer: a fresh random P-256 key (never a fixed one), signing
    the same WebAuthn format as the phone app. The app itself never uses this."""

    def __init__(self, actor: str, label: str | None = None, origin: str = APP_ORIGIN):
        self.actor = actor
        self.origin = origin
        self.credential_id = f"sim-{actor}-{secrets.token_urlsafe(6)}"
        self.label = label or f"Simulated {actor} device"
        self._key = ec.generate_private_key(ec.SECP256R1())
        self.counter = 0

    def public_key_b64(self) -> str:
        der = self._key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        return base64.b64encode(der).decode("ascii")

    def registration(self) -> dict[str, str]:
        return {"credential_id": self.credential_id, "public_key": self.public_key_b64(), "label": self.label,
                "kind": "simulated"}

    def sign(self, hash_hex: str, *, user_verified: bool = True, challenge_hex: str | None = None,
             origin: str | None = None) -> dict[str, str]:
        """A signed approval of `hash_hex`. The keyword arguments let tests build bad ones (no UV, other payment)."""
        origin = origin or self.origin
        self.counter += 1
        client = json.dumps({"type": "webauthn.get", "challenge": challenge_for(challenge_hex or hash_hex),
                             "origin": origin, "crossOrigin": False}, separators=(",", ":")).encode()
        auth = (hashlib.sha256(rp_id_for(origin).encode()).digest() + bytes([0x01 | (0x04 if user_verified else 0)])
                + self.counter.to_bytes(4, "big"))
        sig = self._key.sign(auth + hashlib.sha256(client).digest(), ec.ECDSA(hashes.SHA256()))
        return {"credential_id": self.credential_id, "client_data_json": b64url(client),
                "authenticator_data": b64url(auth), "signature": b64url(sig)}
