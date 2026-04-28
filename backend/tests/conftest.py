import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

FIXTURE_ROOT = Path(__file__).parent / "fixtures"
IMAGE_FIXTURE_SUITES = ("verified_images",)


def pytest_addoption(parser):
    parser.addoption(
        "--fixture-suite",
        action="store",
        default="verified_images",
        choices=("verified_images",),
        help="Verified local image fixture suite to run.",
    )


def _load_entries_from_suite(suite: str) -> list[dict]:
    path = FIXTURE_ROOT / suite / "labels.json"
    if not path.exists():
        return []
    entries: list[dict] = []
    for item in json.loads(path.read_text(encoding="utf-8")):
        item = dict(item)
        item["suite"] = suite
        entries.append(item)
    return entries


def load_fixture_entries(suites: tuple[str, ...] = IMAGE_FIXTURE_SUITES) -> list[dict]:
    entries: list[dict] = []
    for suite in suites:
        entries.extend(_load_entries_from_suite(suite))
    return entries


def pytest_generate_tests(metafunc):
    if "fixture_entry" not in metafunc.fixturenames:
        return
    selected = metafunc.config.getoption("--fixture-suite")
    entries = [
        entry
        for entry in load_fixture_entries()
        if entry["suite"] == selected
    ]
    metafunc.parametrize(
        "fixture_entry",
        entries,
        ids=[f"{entry['suite']}::{entry['id']}" for entry in entries],
    )


@pytest.fixture()
def cached_image_path(fixture_entry: dict) -> Path:
    if fixture_entry.get("fixture_type") != "verified_image":
        pytest.skip("image-backed tests only run against verified local image fixtures")

    local_path = fixture_entry.get("local_path")
    if local_path:
        path = (FIXTURE_ROOT / local_path).resolve()
        if not path.is_file():
            pytest.skip(f"verified image fixture missing: {local_path}")
        return path

    pytest.skip("verified image fixture has no local_path")
