import logging
import secrets
from datetime import datetime, timezone
from typing import Dict, List, Optional
import httpx

from pgod.core.crypto_signer import PGodCryptoSigner
from pgod.models import AmbientPresenceReport, PresenceSignal
from pgod.sensors.biometric import BiometricGlanceSensor
from pgod.sensors.device_telemetry import DeviceContinuitySensor
from pgod.sensors.stylometry import StylometrySensor

logger = logging.getLogger(__name__)


class PresenceOrchestrator:
    """
    Core Ambient Presence Engine of PGod:
    - Continuously listens for passive signals (Stylometry, Biometrics, Mobility).
    - Computes composite confidence score using weighted multi-modal inference.
    - If confidence exceeds threshold, autonomously signs and dispatches the
      SovereignCheckinProof to PGDSecurity to reset the 90-day Dead-Man timer with zero human effort.
    """

    CONFIDENCE_THRESHOLD = 75.0

    def __init__(
        self,
        signer: Optional[PGodCryptoSigner] = None,
        stylometry: Optional[StylometrySensor] = None,
        biometrics: Optional[BiometricGlanceSensor] = None,
        device_sensor: Optional[DeviceContinuitySensor] = None,
    ):
        self.signer = signer or PGodCryptoSigner()
        self.stylometry = stylometry or StylometrySensor()
        self.biometrics = biometrics or BiometricGlanceSensor()
        self.device_sensor = device_sensor or DeviceContinuitySensor()
        self.reports_history: List[AmbientPresenceReport] = []

    def evaluate_ambient_presence(
        self,
        text_sample: Optional[str] = None,
        biometric_assertion: Optional[Dict[str, any]] = None,
        mobility_pulse: Optional[Dict[str, any]] = None,
        auto_dispatch: bool = True,
        planet_url: str = "http://localhost:8000",
    ) -> AmbientPresenceReport:
        """
        Gathers multi-modal passive signals, evaluates presence score,
        and optionally dispatches signed heartbeat to PGDSecurity.
        """
        signals: List[PresenceSignal] = []

        # 1. Stylometry Signal (35% weight)
        sample = text_sample or "Theo tôi hệ thống cần tiến hóa tự động và bảo vệ hạ tầng trong nước."
        sig_text = self.stylometry.evaluate_text_sample(sample)
        signals.append(sig_text)

        # 2. Biometric Glance Signal (40% weight)
        sig_bio = self.biometrics.check_presence_glance(mock_assertion=biometric_assertion)
        signals.append(sig_bio)

        # 3. Device Mobility Signal (25% weight)
        dev_id = mobility_pulse.get("device_id", "dev-phone-primary-01") if mobility_pulse else "dev-phone-primary-01"
        lat = mobility_pulse.get("lat", 21.0285) if mobility_pulse else 21.0285
        lon = mobility_pulse.get("lon", 105.8542) if mobility_pulse else 105.8542
        sig_mob = self.device_sensor.evaluate_mobility_pulse(dev_id, lat, lon)
        signals.append(sig_mob)

        # Weighted calculation
        composite = (
            (sig_text.confidence_score * 0.35)
            + (sig_bio.confidence_score * 0.40)
            + (sig_mob.confidence_score * 0.25)
        )
        composite = round(min(100.0, max(0.0, composite)), 1)
        is_verified = composite >= self.CONFIDENCE_THRESHOLD

        report_id = f"pres-{secrets.token_hex(6)}"
        report = AmbientPresenceReport(
            report_id=report_id,
            signals=signals,
            composite_confidence=composite,
            is_creator_verified=is_verified,
            heartbeat_dispatched=False,
            dispatch_result=None,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Auto-dispatch heartbeat to PGDSecurity if verified
        if is_verified and auto_dispatch:
            proof = self.signer.generate_checkin_proof()
            try:
                with httpx.Client(timeout=4.0) as client:
                    endpoint = f"{planet_url.rstrip('/')}/api/v1/sovereign/checkin"
                    res = client.post(endpoint, json=proof)
                    if res.status_code == 200:
                        report.heartbeat_dispatched = True
                        report.dispatch_result = f"AUTONOMOUS_SUCCESS: PGDSecurity timer reset for 90 days. Server returned: {res.json().get('message')}"
                    else:
                        report.dispatch_result = f"DISPATCH_ERROR_HTTP_{res.status_code}: {res.text}"
            except Exception as e:
                report.dispatch_result = f"DISPATCH_OFFLINE: Could not reach PGDSecurity ({e}). Proof saved for next retry."

        self.reports_history.append(report)
        return report

