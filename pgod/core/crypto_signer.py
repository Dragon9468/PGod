import hashlib
import secrets
from datetime import datetime, timezone
from typing import Dict, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class PGodCryptoSigner:
    """
    Cryptographic Signer for PGod:
    Derives creator's Ed25519 root of trust using VNeID and Biometric seeds,
    and formats standard SovereignCheckinProof tokens to send to PGDSecurity.
    """

    def __init__(
        self,
        vneid_identity_str: str = "VNEID_CREATOR_SOVEREIGN",
        biometric_token_str: str = "BIOMETRIC_FIDO2_SECURE_TOKEN",
        salt: bytes = b"PGDSecurity_Sovereign_Root_Salt_v1",
    ):
        self.vneid_hash = hashlib.sha256(vneid_identity_str.encode("utf-8")).hexdigest()
        ikm = f"VNEID::{vneid_identity_str}##BIOMETRIC::{biometric_token_str}".encode("utf-8")

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=b"PGDSecurity_Sovereign_Ed25519_Seed",
        )
        seed = hkdf.derive(ikm)
        self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
        self.public_key = self.private_key.public_key()
        self.public_key_hex = self.public_key.public_bytes_raw().hex()

    def generate_checkin_proof(self) -> Dict[str, str]:
        """Generates standard SovereignCheckinProof compatible with PGDSecurity server."""
        now = datetime.now(timezone.utc).isoformat()
        proof_id = f"proof-{secrets.token_hex(6)}"
        nonce = secrets.token_hex(16)

        canonical = f"{proof_id}|{self.vneid_hash}|{now}|{nonce}".encode("utf-8")
        sig = self.private_key.sign(canonical).hex()

        return {
            "proof_id": proof_id,
            "vneid_hash": self.vneid_hash,
            "checkin_timestamp": now,
            "nonce": nonce,
            "signature_hex": sig,
        }
