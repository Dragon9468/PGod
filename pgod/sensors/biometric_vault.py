"""Immutable Creator Biometric & Behavioral Vault for PGod."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pgod.core.crypto_signer import PGodCryptoSigner
from pgod.models import CreatorBiometricProfile, KeystrokeDynamicsBaseline
from pgod.sensors.stylometry import StylometrySensor

logger = logging.getLogger(__name__)


class CreatorBiometricVault:
    """Zero-registration immutable biometric and behavioral template for the Creator."""

    DEFAULT_CREATOR_EMAIL = "daophong1205@gmail.com"
    DEFAULT_STYLOMETRIC_MARKERS: List[str] = [
        "theo tôi",
        "bạn hãy",
        "nâng cấp",
        "hệ thống",
        "tiến hóa",
        "tự động",
        "nhẹ máy",
        "triển khai",
        "kiểm tra",
        "bảo vệ",
        "hạ tầng",
        "sinh trắc học",
        "vneid",
    ]
    DEFAULT_HARDWARE_FACTORS: List[str] = [
        "WINDOWS_HELLO_TPM",
        "OPTICAL_FACE_GLANCE",
        "TRUSTED_MOBILE_CORRIDOR",
    ]

    def __init__(
        self,
        creator_email: str = DEFAULT_CREATOR_EMAIL,
        signer: Optional[PGodCryptoSigner] = None,
        stylometry: Optional[StylometrySensor] = None,
    ) -> None:
        self.signer = signer or PGodCryptoSigner()
        self.stylometry = stylometry or StylometrySensor(confidence_threshold=50.0)
        self.profile = CreatorBiometricProfile(
            profile_id="PGOD_CREATOR_SOVEREIGN_V1",
            creator_email=creator_email.strip().lower(),
            vneid_hash=self.signer.vneid_hash,
            ed25519_public_key_hex=self.signer.public_key_hex,
            keystroke_baseline=KeystrokeDynamicsBaseline(),
            stylometric_markers=list(self.DEFAULT_STYLOMETRIC_MARKERS),
            hardware_factors=list(self.DEFAULT_HARDWARE_FACTORS),
            geofence_corridor={
                "lat_range": [8.0, 24.0],
                "lon_range": [102.0, 110.0],
                "timezone_offsets_minutes": [-420, 420],  # UTC+7 (-420 from Date.getTimezoneOffset)
                "preferred_languages": ["vi", "vi-VN", "en-US", "en"],
            },
            is_locked=True,
        )

    def verify_biometric_telemetry(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Verify passive biometric/keystroke/stylometric/corridor signals against the Creator vault."""
        if not isinstance(telemetry, dict):
            return {
                "verified": False,
                "composite_score": 0.0,
                "anomaly_reason": "INVALID_TELEMETRY_PAYLOAD",
                "signals": {},
            }

        email = str(telemetry.get("email") or self.profile.creator_email).strip().lower()
        if email and email != self.profile.creator_email:
            return {
                "verified": False,
                "composite_score": 0.0,
                "anomaly_reason": f"UNAUTHORIZED_CREATOR_EMAIL:{email}",
                "signals": {},
            }

        # 1. Anti-trojan keystroke kinematics check
        sample_count = int(telemetry.get("sample_count", 0) or 0)
        std_dwell_ms = float(telemetry.get("std_dwell_ms", 0.0) or 0.0)
        mean_dwell_ms = float(telemetry.get("mean_dwell_ms", 0.0) or 0.0)
        min_std = self.profile.keystroke_baseline.min_human_dwell_std_ms

        if sample_count >= 5 and std_dwell_ms < min_std:
            return {
                "verified": False,
                "composite_score": 5.0,
                "anomaly_reason": f"TROJAN_MACRO_ZERO_VARIANCE_KEYSTROKES(std={std_dwell_ms:.2f}ms)",
                "signals": {"keystroke_score": 0.0, "sample_count": sample_count},
            }

        keystroke_score = 92.0 if sample_count >= 4 and std_dwell_ms >= min_std else 78.0
        if sample_count >= 4 and 25.0 <= mean_dwell_ms <= 350.0:
            keystroke_score = min(98.0, keystroke_score + 4.0)

        # 2. Stylometric check
        text_sample = str(telemetry.get("text_sample") or "")
        if len(text_sample.strip()) >= 10:
            styl_sig = self.stylometry.evaluate_text_sample(text_sample)
            stylometry_score = max(72.0, styl_sig.confidence_score)
        else:
            stylometry_score = 78.0

        # 3. Timezone / Vietnam geofence corridor check
        tz_offset = telemetry.get("timezone_offset_min", -420)
        corridor_ok = tz_offset in (-420, 420)
        if "lat" in telemetry and "lon" in telemetry:
            lat = float(telemetry["lat"])
            lon = float(telemetry["lon"])
            corridor_ok = corridor_ok and (8.0 <= lat <= 24.0) and (102.0 <= lon <= 110.0)
        corridor_score = 92.0 if corridor_ok else 35.0

        # 4. Ed25519 cryptographic assertion check if provided
        crypto_ok = True
        sig_hex = telemetry.get("ed25519_signature_hex")
        signed_msg = telemetry.get("ed25519_message")
        if sig_hex and signed_msg:
            try:
                self.signer.public_key.verify(
                    bytes.fromhex(str(sig_hex)),
                    str(signed_msg).encode("utf-8"),
                )
            except Exception:
                crypto_ok = False
                return {
                    "verified": False,
                    "composite_score": 0.0,
                    "anomaly_reason": "INVALID_ED25519_SIGNATURE",
                    "signals": {"crypto_ok": False},
                }

        composite = round(
            (keystroke_score * 0.40) + (stylometry_score * 0.35) + (corridor_score * 0.25),
            1,
        )
        verified = composite >= 75.0 and crypto_ok and corridor_ok
        anomaly = None if verified else (
            "OUTSIDE_CREATOR_CORRIDOR" if not corridor_ok else "LOW_BIOMETRIC_CONFIDENCE"
        )
        return {
            "verified": verified,
            "composite_score": composite,
            "anomaly_reason": anomaly,
            "signals": {
                "keystroke_score": keystroke_score,
                "stylometry_score": stylometry_score,
                "corridor_score": corridor_score,
                "crypto_ok": crypto_ok,
            },
        }

    def export_vault_record(self) -> Dict[str, Any]:
        """Export sanitized profile record for Supabase pgdsec_pgod_biometric_vault."""
        return {
            "profile_id": self.profile.profile_id,
            "creator_email": self.profile.creator_email,
            "vneid_hash": self.profile.vneid_hash,
            "ed25519_public_key_hex": self.profile.ed25519_public_key_hex,
            "keystroke_baseline": self.profile.keystroke_baseline.model_dump(),
            "stylometric_markers": self.profile.stylometric_markers,
            "hardware_factors": self.profile.hardware_factors,
            "geofence_corridor": self.profile.geofence_corridor,
            "is_locked": self.profile.is_locked,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def sync_to_supabase(self, supabase_url: str, service_role_key: str) -> Dict[str, Any]:
        """Upsert the immutable Creator vault record into Supabase pgdsec_pgod_biometric_vault."""
        import httpx

        record = self.export_vault_record()
        url = f"{supabase_url.rstrip('/')}/rest/v1/pgdsec_pgod_biometric_vault?on_conflict=profile_id"
        headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation",
        }
        with httpx.Client(timeout=10.0) as client:
            res = client.post(url, json=record, headers=headers)
            res.raise_for_status()
            return {"ok": True, "synced_profile_id": self.profile.profile_id, "rows": res.json()}
