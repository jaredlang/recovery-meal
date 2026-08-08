from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO

import gpxpy
from gpxpy.gpx import GPX

from app.ai.activity_classifier import ActivityClassifier, get_activity_classifier
from app.calculations.energy_v1 import estimate_net_calories
from app.calculations.intensity_v1 import classify_intensity
from app.calculations.met_v1 import met_for


SUPPORTED_ACTIVITIES = {"walking", "hiking", "running", "cycling"}


@dataclass
class ParsedWorkout:
    activity_type: str
    started_at: datetime | None
    duration_seconds: int | None
    distance_meters: float | None
    elevation_gain_meters: float | None
    avg_speed_mps: float | None
    avg_heart_rate: float | None
    max_heart_rate: float | None


def _text_from_gpx(gpx: GPX) -> str:
    values = [gpx.name or "", gpx.description or "", gpx.creator or ""]
    for extension in getattr(gpx, "extensions", None) or []:
        values.extend(element.tag.rsplit("}", 1)[-1] + " " + (element.text or "") for element in extension.iter())
    for track in gpx.tracks:
        values.extend([track.name or "", track.description or ""])
        values.extend([getattr(track, "type", "") or ""])
        for extension in getattr(track, "extensions", None) or []:
            values.extend(element.tag.rsplit("}", 1)[-1] + " " + (element.text or "") for element in extension.iter())
    return " ".join(values).casefold()


def infer_activity_type(gpx: GPX, filename: str, classifier: ActivityClassifier | None = None) -> str:
    context = {
        "filename": filename,
        "creator": gpx.creator or "",
        "name": gpx.name or "",
        "description": gpx.description or "",
        "metadata_and_extension_text": _text_from_gpx(gpx),
    }
    try:
        return (classifier or get_activity_classifier()).classify(context)
    except Exception:
        return "unknown"


def _heart_rate(point) -> float | None:
    values: list[float] = []
    for extension in point.extensions or []:
        for element in extension.iter():
            tag = element.tag.rsplit("}", 1)[-1].casefold()
            if tag in {"hr", "heartrate", "heart_rate"} and element.text:
                try:
                    values.append(float(element.text))
                except ValueError:
                    pass
    return values[0] if values else None


def parse_gpx(content: bytes, filename: str, uploaded_at: datetime | None = None, classifier: ActivityClassifier | None = None) -> ParsedWorkout:
    try:
        gpx = gpxpy.parse(BytesIO(content))
    except Exception as exc:
        raise ValueError("The uploaded file is not a readable GPX file.") from exc
    points = [point for track in gpx.tracks for segment in track.segments for point in segment.points]
    if not points:
        raise ValueError("The GPX file contains no track points.")
    for point in points:
        if point.time is not None and point.time.tzinfo is None:
            point.time = point.time.replace(tzinfo=timezone.utc)
    points.sort(key=lambda point: point.time or datetime.min.replace(tzinfo=timezone.utc))
    timed = [point for point in points if point.time is not None]
    started_at = min((point.time for point in timed), default=None)
    if started_at is None:
        started_at = uploaded_at or datetime.now(timezone.utc)
    duration = None
    if len(timed) >= 2:
        duration = max(1, round((max(point.time for point in timed) - min(point.time for point in timed)).total_seconds()))
    distance = 0.0
    elevation_gain = 0.0
    has_elevation = False
    for previous, current in zip(points, points[1:]):
        if previous.latitude is not None and current.latitude is not None:
            distance += previous.distance_2d(current) or 0
        if previous.elevation is not None and current.elevation is not None:
            has_elevation = True
            if current.elevation > previous.elevation:
                elevation_gain += current.elevation - previous.elevation
    hrs = [hr for point in points if (hr := _heart_rate(point)) is not None]
    speed = distance / duration if duration else None
    return ParsedWorkout(
        activity_type=infer_activity_type(gpx, filename, classifier),
        started_at=started_at,
        duration_seconds=duration,
        distance_meters=distance,
        elevation_gain_meters=elevation_gain if has_elevation else None,
        avg_speed_mps=speed,
        avg_heart_rate=sum(hrs) / len(hrs) if hrs else None,
        max_heart_rate=max(hrs) if hrs else None,
    )


def calculate_fields(parsed: ParsedWorkout, age: int, weight_kg: float) -> dict:
    if parsed.activity_type not in SUPPORTED_ACTIVITIES or parsed.duration_seconds is None:
        return {"met_value": None, "intensity": None, "estimated_calories_low": None, "estimated_calories_high": None}
    met = met_for(parsed.activity_type, parsed.avg_speed_mps)
    intensity = classify_intensity(parsed.avg_heart_rate, age, met)
    low, high = estimate_net_calories(met, weight_kg, parsed.duration_seconds)
    return {"met_value": met, "intensity": intensity, "estimated_calories_low": low, "estimated_calories_high": high}
