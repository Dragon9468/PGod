import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pgod.models import (
    DeviceReplacementRequest,
    DeviceStatus,
    PresenceSignal,
    SensorType,
    TrustedDevice,
)

logger = logging.getLogger(__name__)


class DeviceContinuitySensor:
    """
    Mobile Device Telemetry, GPS Mobility & Device Continuity Sensor:
    - Tracks smartphone and personal endpoint geofencing and routine movement.
    - Prevents sudden lockout when phone breaks or is replaced via the Device Replacement Protocol.
    """

    # Normal activity bounds in Vietnam (e.g. Greater Hanoi & TP.HCM metro regions)
    VIETNAM_LAT_RANGE = (8.0, 24.0)
    VIETNAM_LON_RANGE = (102.0, 110.0)

    def __init__(self, state_file: Optional[Path] = None, recovery_seed: str = "SOVEREIGN_MASTER_RECOVERY_SEED_001"):
        self.state_file = state_file or Path(".pgod_device_vault.json")
        self.recovery_seed_hash = hashlib.sha256(recovery_seed.encode("utf-8")).hexdigest()
        self.devices: Dict[str, TrustedDevice] = {}
        self._load_devices()

    def _load_devices(self):
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                for d_id, d_data in data.items():
                    self.devices[d_id] = TrustedDevice(**d_data)
            except Exception:
                pass
        if not self.devices:
            # Default primary smartphone
            default_phone = TrustedDevice(
                device_id="dev-phone-primary-01",
                device_name="Creator Personal Smartphone",
                device_type="SMARTPHONE",
                registered_at=datetime.now(timezone.utc).isoformat(),
                last_seen_at=datetime.now(timezone.utc).isoformat(),
                last_latitude=21.0285,  # Hanoi baseline
                last_longitude=105.8542,
                status=DeviceStatus.ACTIVE,
            )
            self.devices[default_phone.device_id] = default_phone
            self._save_devices()

    def _save_devices(self):
        try:
            payload = {d_id: d.model_dump() for d_id, d in self.devices.items()}
            self.state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed saving devices state: {e}")

    def evaluate_mobility_pulse(
        self,
        device_id: str,
        latitude: float,
        longitude: float,
    ) -> PresenceSignal:
        """
        Evaluates a GPS pulse from an active trusted device.
        Verifies that movement corridor is realistic and consistent with normal presence.
        """
        if device_id not in self.devices:
            return PresenceSignal(
                sensor_type=SensorType.DEVICE_MOBILITY,
                confidence_score=0.0,
                summary=f"Unrecognized device ID '{device_id}' attempted mobility pulse.",
                details={"status": "DEVICE_NOT_ENROLLED"},
            )

        dev = self.devices[device_id]
        if dev.status != DeviceStatus.ACTIVE:
            return PresenceSignal(
                sensor_type=SensorType.DEVICE_MOBILITY,
                confidence_score=0.0,
                summary=f"Device '{dev.device_name}' is {dev.status.value}. Signal rejected.",
                details={"status": dev.status.value},
            )

        # Check geographic boundaries (Vietnam national territory)
        in_vietnam = (
            self.VIETNAM_LAT_RANGE[0] <= latitude <= self.VIETNAM_LAT_RANGE[1]
            and self.VIETNAM_LON_RANGE[0] <= longitude <= self.VIETNAM_LON_RANGE[1]
        )

        now = datetime.now(timezone.utc).isoformat()
        dev.last_seen_at = now
        dev.last_latitude = latitude
        dev.last_longitude = longitude
        self._save_devices()

        if in_vietnam:
            confidence = 90.0
            summary = f"Routine mobility verified for '{dev.device_name}' ({latitude:.4f}, {longitude:.4f})."
        else:
            confidence = 45.0  # International travel or unusual coordinates
            summary = f"Geofence anomaly: Location outside standard domestic corridor ({latitude}, {longitude})."

        return PresenceSignal(
            sensor_type=SensorType.DEVICE_MOBILITY,
            confidence_score=confidence,
            summary=summary,
            details={
                "device_id": device_id,
                "device_name": dev.device_name,
                "latitude": latitude,
                "longitude": longitude,
                "in_domestic_corridor": in_vietnam,
            },
        )

    def execute_device_replacement(self, request: DeviceReplacementRequest) -> Dict[str, any]:
        """
        Device Replacement Protocol:
        If creator's phone breaks or is suddenly replaced, authenticates with recovery seed hash,
        retires the old device, and seamlessly enrolls the replacement device without locking out the Dead-Man switch.
        """
        if request.recovery_seed_hash != self.recovery_seed_hash:
            return {
                "success": False,
                "reason": "INVALID_RECOVERY_PROOF: Seed hash does not match Creator Master Recovery Seed.",
            }

        old_dev = self.devices.get(request.old_device_id)
        if old_dev:
            old_dev.status = DeviceStatus.REPLACED

        now = datetime.now(timezone.utc).isoformat()
        new_dev = TrustedDevice(
            device_id=request.new_device_id,
            device_name=request.new_device_name,
            device_type="SMARTPHONE",
            registered_at=now,
            last_seen_at=now,
            status=DeviceStatus.ACTIVE,
        )
        self.devices[new_dev.device_id] = new_dev
        self._save_devices()

        return {
            "success": True,
            "message": f"Successfully replaced '{request.old_device_id}' with '{new_dev.device_name}'.",
            "active_device_id": new_dev.device_id,
            "transition_timestamp": now,
        }
