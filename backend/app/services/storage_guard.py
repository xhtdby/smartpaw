"""Persistent storage budget, compression, and compact text helpers."""

from __future__ import annotations

import base64
import gzip
import io
import os
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import get_settings

MB = 1024 * 1024
TEXT_GZIP_PREFIX = "mdgz:"


class StorageBudgetExceeded(RuntimeError):
    """Raised when a write would exceed the configured persistent volume budget."""


class StoredImageError(ValueError):
    """Raised when an uploaded image cannot be safely stored."""


def encode_markdown_text_lossless(text: str | None) -> str:
    """Return a smaller lossless storage representation when gzip helps.

    The plain text is preserved exactly after decode. Short text usually stays
    plain because base64+gzip can be larger than UTF-8 for small strings.
    """
    if not text:
        return ""
    raw = text.encode("utf-8")
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    encoded = TEXT_GZIP_PREFIX + base64.b64encode(compressed).decode("ascii")
    return encoded if len(encoded.encode("utf-8")) < len(raw) else text


def decode_markdown_text_lossless(stored: str | None) -> str:
    if not stored:
        return ""
    if not stored.startswith(TEXT_GZIP_PREFIX):
        return stored
    payload = stored[len(TEXT_GZIP_PREFIX) :]
    return gzip.decompress(base64.b64decode(payload.encode("ascii"))).decode("utf-8")


def directory_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size

    total = 0
    for root, _, files in os.walk(path):
        for filename in files:
            file_path = Path(root) / filename
            try:
                total += file_path.stat().st_size
            except OSError:
                continue
    return total


def storage_snapshot(settings: Any | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    data_dir = Path(settings.data_dir)
    uploads_dir = Path(settings.uploads_dir)
    db_path = Path(settings.db_path)
    data_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    data_used = directory_size_bytes(data_dir)
    uploads_used = directory_size_bytes(uploads_dir)
    db_size = db_path.stat().st_size if db_path.exists() else 0
    disk_usage = shutil.disk_usage(data_dir)

    budget_bytes = int(settings.persistent_storage_budget_mb) * MB
    soft_limit_bytes = int(settings.persistent_storage_soft_limit_mb) * MB
    return {
        "data_dir": str(data_dir),
        "uploads_dir": str(uploads_dir),
        "db_path": str(db_path),
        "budget_bytes": budget_bytes,
        "soft_limit_bytes": soft_limit_bytes,
        "used_bytes": data_used,
        "uploads_bytes": uploads_used,
        "db_bytes": db_size,
        "remaining_soft_bytes": max(0, soft_limit_bytes - data_used),
        "disk_free_bytes": disk_usage.free,
    }


def assert_storage_capacity(extra_bytes: int, settings: Any | None = None) -> None:
    settings = settings or get_settings()
    snapshot = storage_snapshot(settings)
    min_free_bytes = int(settings.persistent_storage_min_free_mb) * MB
    if snapshot["used_bytes"] + extra_bytes > snapshot["soft_limit_bytes"]:
        raise StorageBudgetExceeded("persistent_storage_soft_limit")
    if snapshot["disk_free_bytes"] - extra_bytes < min_free_bytes:
        raise StorageBudgetExceeded("persistent_storage_min_free")


def check_writable(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".indieaid_write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _encode_jpeg(image: Image.Image, max_edge: int, quality: int) -> bytes:
    candidate = image.copy()
    candidate.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    candidate.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def compress_image_for_storage(image_bytes: bytes, settings: Any | None = None) -> bytes:
    """Convert an uploaded image into a bounded, metadata-stripped JPEG."""
    settings = settings or get_settings()
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise StoredImageError("image_invalid_format") from exc

    target_bytes = int(settings.stored_report_image_target_kb) * 1024
    hard_max_bytes = int(settings.stored_report_image_hard_max_kb) * 1024
    base_edge = int(settings.stored_report_image_max_edge)
    base_quality = int(settings.stored_report_image_quality)

    best: bytes | None = None
    edge_candidates = [base_edge, 840, 720, 640]
    quality_candidates = [base_quality, 62, 56, 50, 45]
    for edge in sorted({edge for edge in edge_candidates if edge > 0}, reverse=True):
        for quality in sorted({q for q in quality_candidates if 35 <= q <= 95}, reverse=True):
            encoded = _encode_jpeg(image, edge, quality)
            if best is None or len(encoded) < len(best):
                best = encoded
            if len(encoded) <= target_bytes:
                return encoded

    if best is None or len(best) > hard_max_bytes:
        raise StoredImageError("image_too_large_after_compression")
    return best
