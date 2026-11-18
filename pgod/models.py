from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SensorType(str, Enum):
    STYLOMETRY = "STYLOMETRY"
    BIOMETRIC_GLANCE = "BIOMETRIC_GLANCE"
    DEVICE_MOBILITY = "DEVICE_MOBILITY"
    AI_INTERACTION = "AI_INTERACTION"


class DeviceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REPLACED = "REPLACED"
    REVOKED = "REVOKED"
    MIGRATED_AUTOMATICALLY = "MIGRATED_AUTOMATICALLY"


class PresenceSignal(BaseModel):
    sensor_type: SensorType
    confidence_score: float = Field(ge=0.0, le=100.0)
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AmbientPresenceReport(BaseModel):
    report_id: str
    signals: List[PresenceSignal]
    composite_confidence: float = Field(ge=0.0, le=100.0)
    is_creator_verified: bool
    heartbeat_dispatched: bool = False
    dispatch_result: Optional[str] = None
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TrustedDevice(BaseModel):
    device_id: str
    device_name: str
    device_type: str  # SMARTPHONE, LAPTOP, WORKSTATION
    bound_google_account: Optional[str] = None
    registered_at: str
    last_seen_at: str
    last_latitude: Optional[float] = None
    last_longitude: Optional[float] = None
    status: DeviceStatus = DeviceStatus.ACTIVE


class DeviceReplacementRequest(BaseModel):
    old_device_id: str
    new_device_id: str
    new_device_name: str
    recovery_seed_hash: str
    reason: str = "Device Damaged / Replaced"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class KeystrokeDynamicsBaseline(BaseModel):
    min_human_dwell_std_ms: float = 1.5
    typical_dwell_ms_range: List[float] = Field(default_factory=lambda: [35.0, 260.0])
    typical_flight_ms_range: List[float] = Field(default_factory=lambda: [45.0, 650.0])


class CreatorBiometricProfile(BaseModel):
    profile_id: str = "PGOD_CREATOR_SOVEREIGN_V1"
    creator_email: str = "daophong1205@gmail.com"
    vneid_hash: str
    ed25519_public_key_hex: str
    keystroke_baseline: KeystrokeDynamicsBaseline = Field(default_factory=KeystrokeDynamicsBaseline)
    stylometric_markers: List[str] = Field(default_factory=list)
    hardware_factors: List[str] = Field(default_factory=list)
    geofence_corridor: Dict[str, Any] = Field(default_factory=dict)
    is_locked: bool = True
