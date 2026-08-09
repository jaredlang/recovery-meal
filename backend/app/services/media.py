from pathlib import Path

from app.config import settings


def media_root() -> Path:
    root = Path(settings.upload_dir) / "media"
    try:
        root.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Docker uses /app/uploads; local Windows development may inherit that
        # value from .env even though the absolute container path is unwritable.
        root = Path.cwd() / "uploads" / "media"
        root.mkdir(parents=True, exist_ok=True)
    return root


def media_url(filename: str | None) -> str | None:
    return f"/media/{filename}" if filename else None


def remove_media(filename: str | None) -> None:
    if not filename:
        return
    candidate = (media_root() / filename).resolve()
    root = media_root().resolve()
    if root in candidate.parents and candidate.is_file():
        candidate.unlink()
