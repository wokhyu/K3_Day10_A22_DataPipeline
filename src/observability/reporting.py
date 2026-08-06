from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import ensure_parent, write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a markdown report for the baseline phase."""
    report_path = Path(report_path)
    ensure_parent(report_path)

    lines = [
        "# Phase 1 Report",
        "",
        "## Source Summary",
        "",
    ]
    for key, value in source_summary.items():
        lines.append(f"- **{key}**: {value}")

    lines.extend(
        [
            "",
            "## Evaluation Metrics",
            "",
        ]
    )
    for key, value in metrics.items():
        lines.append(f"- **{key}**: {value}")

    lines.extend(
        [
            "",
            "## Data Quality",
            "",
        ]
    )
    for key, value in quality.items():
        lines.append(f"- **{key}**: {value}")

    lines.extend(
        [
            "",
            "## Freshness",
            "",
        ]
    )
    for key, value in freshness.items():
        lines.append(f"- **{key}**: {value}")

    write_text(report_path, "\n".join(lines) + "\n")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write a markdown report comparing baseline, corrupted, and repaired states."""
    report_path = Path(report_path)
    ensure_parent(report_path)

    def metric_block(title: str, metrics: dict[str, Any]) -> list[str]:
        lines = [f"## {title}", ""]
        for key, value in metrics.items():
            lines.append(f"- **{key}**: {value}")
        return lines

    lines = [
        "# Corruption Comparison Report",
        "",
        "## Summary",
        "",
        "This report compares the baseline, corrupted, and repaired datasets for retrieval and data quality performance.",
        "",
    ]
    lines.extend(metric_block("Baseline Metrics", baseline_metrics))
    lines.extend(["", *metric_block("Corrupted Metrics", corrupted_metrics)])
    lines.extend(["", *metric_block("Repaired Metrics", repaired_metrics)])
    lines.extend(["", "## Quality Comparison", ""])
    lines.append(f"- **Corrupted quality passed**: {corrupted_quality.get('passed')}")
    lines.append(f"- **Repaired quality passed**: {repaired_quality.get('passed')}")
    lines.extend(["", "## Freshness Comparison", ""])
    lines.append(f"- **Corrupted freshness is_fresh**: {corrupted_freshness.get('is_fresh')}")
    lines.append(f"- **Repaired freshness is_fresh**: {repaired_freshness.get('is_fresh')}")

    write_text(report_path, "\n".join(lines) + "\n")
