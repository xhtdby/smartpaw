import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def pytest_addoption(parser):
    parser.addoption(
        "--fixture-suite",
        action="store",
        default="all",
        choices=("all", "quick", "detailed"),
        help="Image fixture suite to run.",
    )


def load_fixture_entries() -> list[dict]:
    root = Path(__file__).parent / "fixtures"
    entries: list[dict] = []
    for suite in ("quick", "detailed"):
        path = root / suite / "labels.json"
        if not path.exists():
            continue
        for item in json.loads(path.read_text(encoding="utf-8")):
            item = dict(item)
            item["suite"] = suite
            entries.append(item)
    return entries


def pytest_generate_tests(metafunc):
    if "fixture_entry" not in metafunc.fixturenames:
        return
    selected = metafunc.config.getoption("--fixture-suite")
    entries = [
        entry
        for entry in load_fixture_entries()
        if selected == "all" or entry["suite"] == selected
    ]
    metafunc.parametrize(
        "fixture_entry",
        entries,
        ids=[f"{entry['suite']}::{entry['id']}" for entry in entries],
    )


@pytest.fixture(scope="session")
def image_cache_dir() -> Path:
    path = Path(__file__).parent / "fixtures" / "_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture()
def cached_image_path(fixture_entry: dict, image_cache_dir: Path) -> Path:
    url = fixture_entry["url"]
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    suffix = Path(url.split("?", 1)[0]).suffix or ".jpg"
    target = image_cache_dir / f"{digest}{suffix}"
    if target.exists() and target.stat().st_size > 0:
        return target

    if os.getenv("SMARTPAW_SKIP_IMAGE_DOWNLOADS") == "1":
        pytest.skip("image cache missing and downloads disabled")

    try:
        request = urllib.request.Request(url, headers={"User-Agent": "SmartPaw-tests/1.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            target.write_bytes(response.read())
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        pytest.skip(f"offline or fixture image unavailable: {exc}")

    return target
