import hashlib
from unittest.mock import MagicMock, patch
import pytest

from pgod.core.crypto_signer import PGodCryptoSigner
from pgod.core.orchestrator import PresenceOrchestrator
from pgod.models import (
    DeviceReplacementRequest,
    DeviceStatus,
    PresenceSignal,
    SensorType,
)
from pgod.sensors.biometric import BiometricGlanceSensor
from pgod.sensors.device_telemetry import DeviceContinuitySensor
from pgod.sensors.stylometry import StylometrySensor


def test_stylometry_sensor_authentic_markers():
    """Verifies that Creator's distinctive phrasing triggers high stylometric confidence."""
    sensor = StylometrySensor(confidence_threshold=70.0)

    # Sample containing authentic Creator phrases
    authentic_text = (
        "Theo tôi hệ thống cần tiến hóa tự động, triển khai bảo vệ trong nước "
        "kết hợp VNeID và sinh trắc học để phòng ngừa thảm họa."
    )
    sig = sensor.evaluate_text_sample(authentic_text)
    assert sig.sensor_type == SensorType.STYLOMETRY
    assert sig.confidence_score >= 70.0
    assert sig.details["is_consistent"] is True

    # Generic or too short text
    sig_short = sensor.evaluate_text_sample("hi")
    assert sig_short.confidence_score == 0.0


def test_biometric_glance_sensor():
    """Verifies that BiometricGlanceSensor confirms human presence and liveness."""
    sensor = BiometricGlanceSensor(required_confidence=85.0)

    # Positive match
    sig_ok = sensor.check_presence_glance(mock_assertion={"matched": True, "score": 96.0})
    assert sig_ok.confidence_score == 96.0
    assert sig_ok.details["liveness_confirmed"] is True

    # Failed match
    sig_fail = sensor.check_presence_glance(mock_assertion={"matched": False, "score": 15.0})
    assert sig_fail.confidence_score == 15.0
    assert sig_fail.details["liveness_confirmed"] is False


def test_device_continuity_mobility_and_replacement(tmp_path):
    """Verifies GPS corridor monitoring and the Device Replacement Protocol."""
    state_file = tmp_path / "devices.json"
    sensor = DeviceContinuitySensor(state_file=state_file, recovery_seed="SECRET_SEED_123")

    # 1. Normal mobility pulse in Hanoi
    sig_hanoi = sensor.evaluate_mobility_pulse("dev-phone-primary-01", 21.0285, 105.8542)
    assert sig_hanoi.confidence_score >= 80.0
    assert sig_hanoi.details["in_domestic_corridor"] is True

    # 2. Out of region anomaly
    sig_anomaly = sensor.evaluate_mobility_pulse("dev-phone-primary-01", 48.8566, 2.3522)  # Paris
    assert sig_anomaly.confidence_score < 50.0

    # 3. Device Replacement with valid recovery seed
    valid_seed_hash = hashlib.sha256("SECRET_SEED_123".encode("utf-8")).hexdigest()
    req = DeviceReplacementRequest(
        old_device_id="dev-phone-primary-01",
        new_device_id="dev-phone-new-gen",
        new_device_name="Creator Upgraded Phone",
        recovery_seed_hash=valid_seed_hash,
    )
    res = sensor.execute_device_replacement(req)
    assert res["success"] is True
    assert sensor.devices["dev-phone-primary-01"].status == DeviceStatus.REPLACED
    assert sensor.devices["dev-phone-new-gen"].status == DeviceStatus.ACTIVE

    # 4. Device Replacement with invalid seed fails
    req_bad = DeviceReplacementRequest(
        old_device_id="dev-phone-new-gen",
        new_device_id="dev-phone-fake",
        new_device_name="Fake Phone",
        recovery_seed_hash="BAD_HASH",
    )
    res_bad = sensor.execute_device_replacement(req_bad)
    assert res_bad["success"] is False


def test_pgod_crypto_signer_compatibility():
    """Verifies that PGod produces valid Ed25519 SovereignCheckinProof tokens."""
    signer = PGodCryptoSigner(
        vneid_identity_str="VNEID_CREATOR_SOVEREIGN",
        biometric_token_str="BIOMETRIC_FIDO2_SECURE_TOKEN",
    )
    proof = signer.generate_checkin_proof()
    assert "proof_id" in proof
    assert "signature_hex" in proof
    assert "vneid_hash" in proof
    assert len(proof["signature_hex"]) == 128  # Ed25519 hex signature length


def test_presence_orchestrator_aggregation_and_auto_dispatch():
    """Verifies multi-modal presence scoring and autonomous dispatch to PGDSecurity."""
    orchestrator = PresenceOrchestrator()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"success": True, "message": "Dead-Man timer renewed for 90 days."}

    with patch("httpx.Client.post", return_value=mock_resp):
        report = orchestrator.evaluate_ambient_presence(
            text_sample="Theo tôi hệ thống cần tự tiến hóa và bảo vệ hạ tầng trong nước.",
            biometric_assertion={"matched": True, "score": 95.0},
            mobility_pulse={"device_id": "dev-phone-primary-01", "lat": 21.0285, "lon": 105.8542},
            auto_dispatch=True,
            planet_url="http://localhost:8000",
        )

        assert report.is_creator_verified is True
        assert report.composite_confidence >= 80.0
        assert report.heartbeat_dispatched is True
        assert "AUTONOMOUS_SUCCESS" in report.dispatch_result

