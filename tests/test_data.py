"""data/*.json の構造妥当性テスト"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_device_db_shape():
    db = _load("device-db.json")
    assert isinstance(db, dict) and len(db) >= 5
    for name, entry in db.items():
        assert "type" in entry, f"{name} missing 'type'"
        assert "available_on" in entry, f"{name} missing 'available_on'"
        assert isinstance(entry["available_on"], list)
        assert "description_ja" in entry, f"{name} missing 'description_ja'"


def test_hardware_db_shape():
    db = _load("hardware-db.json")
    assert isinstance(db, dict)
    assert "move" in db
    move = db["move"]
    assert "versions" in move
    assert "2.0.0" in move["versions"]
    v200 = move["versions"]["2.0.0"]
    assert v200.get("audio_tracks_supported") is True


def test_release_notes_db_shape():
    db = _load("release-notes-db.json")
    assert isinstance(db, list) and len(db) >= 1
    products = {r["product"] for r in db}
    assert {"move", "live"}.issubset(products)
    for r in db:
        assert "version" in r
        assert "release_date" in r
        assert "highlights_ja" in r and isinstance(r["highlights_ja"], list)


def test_lom_db_shape():
    db = _load("lom-db.json")
    required = {"Application", "Song", "Track", "Clip", "Device"}
    assert required.issubset(set(db.keys())), f"missing: {required - set(db.keys())}"
    for name, cls in db.items():
        assert "description_ja" in cls
        # parent は null か文字列
        assert "parent" in cls


def test_glossary_db_shape():
    db = _load("glossary-db.json")
    assert isinstance(db, dict) and len(db) >= 5
    for term, entry in db.items():
        assert "ja" in entry, f"{term} missing 'ja'"
        assert "description_ja" in entry, f"{term} missing 'description_ja'"


def test_pattern_db_shape():
    db = _load("pattern-db.json")
    assert isinstance(db, list) and len(db) >= 3
    for p in db:
        assert "id" in p
        assert "name" in p
        assert "applicable_products" in p
        assert isinstance(p["applicable_products"], list)
