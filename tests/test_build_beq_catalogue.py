import json
from pathlib import Path

import pytest

from tools.build_beq_catalogue import build


def test_build_writes_compact_index_and_on_demand_entries(tmp_path: Path):
    source = tmp_path / "source.json"
    output = tmp_path / "public"
    source.write_text(json.dumps([{
        "title": "Example Film",
        "underlying": "Example Film (2024)",
        "author": "Author",
        "year": 2024,
        "audioTypes": ["Atmos"],
        "content_type": "film",
        "filters": [{
            "type": "PeakingEQ", "freq": 20, "gain": 4.5, "q": 1.2,
            "biquads": {"96000": {"b": ["1"], "a": ["1"]}},
        }],
    }]), encoding="utf-8")

    manifest = build(source, output)
    assert manifest["entry_count"] == 1
    assert manifest["schema_version"] == 1

    index = json.loads((output / manifest["index"]).read_text(encoding="utf-8"))
    assert index["categories"] == {"film": [0]}
    assert index["entries"][0]["title"] == "Example Film"
    assert "filters" not in index["entries"][0]

    payload = json.loads(
        (output / manifest["version"] / "entries" /
         f"{index['entries'][0]['id']}.json").read_text(encoding="utf-8")
    )
    assert payload["underlying"] == "Example Film (2024)"
    assert "biquads" not in payload["filters"][0]
    assert payload["filters"] == [{
        "type": "PeakingEQ", "freq": 20, "gain": 4.5, "q": 1.2,
    }]


@pytest.mark.parametrize("records", [[], {}, [None], [{"title": "Missing filters"}]])
def test_rejects_invalid_source_records(tmp_path: Path, records):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(records), encoding="utf-8")
    with pytest.raises((ValueError, TypeError)):
        build(source, tmp_path / "public")
