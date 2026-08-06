from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run a basic set of data quality checks and persist the result as JSON."""
    total_rows = int(len(df))
    missing_paper_id = int(df["paper_id"].isna().sum()) if "paper_id" in df.columns else 0
    duplicate_paper_id = int(
        df["paper_id"].duplicated(keep=False).sum() // 2
        if "paper_id" in df.columns
        else 0
    )
    missing_title = int(df["title"].isna().sum()) if "title" in df.columns else 0
    empty_summary = int(
        df["summary"].fillna("").str.strip().eq("").sum() if "summary" in df.columns else 0
    )
    stale_rows = int(
        df["age_days"].fillna(0).gt(settings.freshness_threshold_days).sum() if "age_days" in df.columns else 0
    )

    quality_report = {
        "report_name": report_name,
        "total_rows": total_rows,
        "missing_paper_id": missing_paper_id,
        "duplicate_paper_id": duplicate_paper_id,
        "missing_title": missing_title,
        "empty_summary": empty_summary,
        "stale_rows": stale_rows,
        "passed": all(
            [
                total_rows > 0,
                missing_paper_id == 0,
                duplicate_paper_id == 0,
                missing_title == 0,
                empty_summary == 0,
                stale_rows == 0,
            ]
        ),
    }

    quality_path = Path(settings.paths.quality_dir) / f"{report_name}.json"
    ensure_parent(quality_path)
    write_json(quality_path, quality_report)
    return quality_report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build a freshness summary and store it as JSON."""
    published_col = df["published"] if "published" in df.columns else pd.Series([None] * len(df))
    parsed_dates = []
    for value in published_col:
        if pd.isna(value):
            parsed_dates.append(None)
            continue
        if isinstance(value, datetime):
            parsed_dates.append(value)
        else:
            try:
                parsed_dates.append(pd.to_datetime(value, utc=True))
            except Exception:
                parsed_dates.append(None)

    valid_dates = [date for date in parsed_dates if date is not None]
    latest_published = max(valid_dates).isoformat() if valid_dates else None
    oldest_published = min(valid_dates).isoformat() if valid_dates else None

    if "age_days" in df.columns:
        stale_rows = int(df["age_days"].fillna(0).gt(settings.freshness_threshold_days).sum())
    else:
        stale_rows = 0

    freshness_report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": int(len(df)),
        "is_fresh": stale_rows == 0 and len(valid_dates) > 0,
    }

    report_path = Path(report_path)
    ensure_parent(report_path)
    write_json(report_path, freshness_report)
    return freshness_report
