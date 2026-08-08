from collections.abc import Sequence


def _lookup(mph: float, bands: Sequence[tuple[float, float | None, float]], default: float) -> float:
    for low, high, met in bands:
        if mph >= low and (high is None or mph < high):
            return met
    return default


def met_for(activity_type: str, speed_mps: float | None) -> float:
    mph = (speed_mps or 0) * 2.236936
    if activity_type == "cycling":
        return _lookup(mph, [(0, 10, 4.0), (10, 12, 6.8), (12, 14, 8.0), (14, 16, 10.0), (16, 20, 12.0), (20, None, 16.8)], 4.0)
    if activity_type == "running":
        return _lookup(mph, [(0, 3.8, 3.3), (3.8, 4.3, 6.5), (4.3, 4.9, 7.8), (4.9, 5.5, 8.5), (5.5, 5.9, 9.0), (5.9, 6.4, 9.3), (6.4, 7.0, 10.5), (7.0, 7.5, 11.0), (7.5, 8.0, 11.8), (8.0, 8.6, 12.0), (8.6, 9.0, 12.5), (9.0, 9.3, 13.0), (9.3, 10.01, 14.8), (10.01, None, 16.8)], 3.3)
    if activity_type == "walking":
        return _lookup(mph, [(0, 2.0, 2.3), (2.0, 2.5, 2.8), (2.5, 2.8, 3.0), (2.8, 3.5, 3.8), (3.5, 4.0, 4.8), (4.0, 4.5, 5.5), (4.5, 5.0, 7.0), (5.0, None, 8.5)], 2.3)
    if activity_type == "hiking":
        return 3.8 if mph < 2.0 else 5.3
    raise ValueError("Unsupported activity type")

