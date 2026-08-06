from pathlib import Path
import sys
from types import SimpleNamespace

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report, generate_phase1_report


def test_observability_outputs(tmp_path):
    df = pd.DataFrame(
        [
            {
                "paper_id": "p1",
                "title": "Alpha",
                "summary": "A short summary",
                "published": "2024-01-01",
                "age_days": 10,
            },
            {
                "paper_id": None,
                "title": "Beta",
                "summary": "",
                "published": "2023-01-01",
                "age_days": 400,
            },
            {
                "paper_id": "p1",
                "title": "Gamma",
                "summary": "Another summary",
                "published": "2022-01-01",
                "age_days": 1000,
            },
        ]
    )

    settings = SimpleNamespace(
        freshness_threshold_days=180,
        paths=SimpleNamespace(quality_dir=tmp_path, freshness_report=tmp_path / "freshness_report.json"),
    )

    quality = run_data_quality_checks(df, settings, "sample_quality")
    freshness = build_freshness_report(df, settings, tmp_path / "freshness_report.json")

    assert quality["total_rows"] == 3
    assert quality["missing_paper_id"] == 1
    assert quality["duplicate_paper_id"] == 1
    assert quality["missing_title"] == 0
    assert quality["empty_summary"] == 1
    assert quality["stale_rows"] == 2
    assert quality["passed"] is False

    assert freshness["total_rows"] == 3
    assert freshness["stale_rows"] == 2
    assert freshness["is_fresh"] is False
    assert (tmp_path / "freshness_report.json").exists()

    phase1_report = tmp_path / "phase1.md"
    generate_phase1_report(phase1_report, {"source": "crossref"}, {"retrieval_hit_rate": 0.8}, quality, freshness)
    assert phase1_report.exists()

    corruption_report = tmp_path / "corruption.md"
    generate_corruption_report(
        corruption_report,
        {"retrieval_hit_rate": 0.8},
        {"retrieval_hit_rate": 0.4},
        {"retrieval_hit_rate": 0.75},
        {"passed": False},
        {"passed": True},
        {"is_fresh": False},
        {"is_fresh": True},
    )
    assert corruption_report.exists()
