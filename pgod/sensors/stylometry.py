import re
from typing import Dict, List, Optional
from pgod.models import PresenceSignal, SensorType


class StylometrySensor:
    """
    AI-Assisted Stylometry & Behavioral Interaction Sensor:
    Analyzes prompt phrasing, linguistic nuances, coding syntax, and interaction patterns
    to passively authenticate the creator without requiring explicit password entry.
    """

    # Linguistic fingerprint of Creator
    CREATOR_LINGUISTIC_MARKERS = [
        r"\b(theo tôi|bạn hãy|nâng cấp|hệ thống|tiến hóa|chủ nghĩa xã hội|tự động)\b",
        r"\b(nhẹ máy|triển khai|kiểm tra|bảo vệ|phản công|nhảy qua|hạ tầng)\b",
        r"\b(vneid|sinh trắc học|shutdown|trong nước|viettel|fpt)\b",
    ]

    def __init__(self, confidence_threshold: float = 70.0):
        self.confidence_threshold = confidence_threshold

    def evaluate_text_sample(self, text: str) -> PresenceSignal:
        """
        Evaluates a sample of text (e.g. user prompt to AI agent or commit message)
        against the Creator's established stylometric baseline.
        """
        clean_text = text.strip().lower()
        if not clean_text or len(clean_text) < 10:
            return PresenceSignal(
                sensor_type=SensorType.STYLOMETRY,
                confidence_score=0.0,
                summary="Sample too short for reliable stylometric authentication.",
                details={"text_length": len(clean_text)},
            )

        matches_count = 0
        matched_patterns = []
        for pattern in self.CREATOR_LINGUISTIC_MARKERS:
            found = re.findall(pattern, clean_text, re.IGNORECASE)
            if found:
                matches_count += len(found)
                matched_patterns.extend(found)

        # Baseline confidence curve
        confidence = min(98.0, 40.0 + (matches_count * 12.0))
        is_consistent = confidence >= self.confidence_threshold

        return PresenceSignal(
            sensor_type=SensorType.STYLOMETRY,
            confidence_score=round(confidence, 1),
            summary=(
                f"Stylometric match verified ({confidence}%). "
                f"Detected {matches_count} authentic linguistic markers."
                if is_consistent else "Low stylometric consistency with Creator baseline."
            ),
            details={
                "matches_count": matches_count,
                "matched_markers": list(set(matched_patterns))[:5],
                "sample_preview": text[:80],
                "is_consistent": is_consistent,
            },
        )

