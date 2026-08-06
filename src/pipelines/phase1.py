from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def _load_or_fetch_raw_records(settings) -> list[PaperRecord]:
    raw_records_path = settings.paths.raw_records_json
    should_fetch = settings.refresh_source or not raw_records_path.exists()
    if should_fetch:
        return fetch_source_records(settings)
    return load_raw_records(raw_records_path)


def _ensure_index_columns(df, records: list[PaperRecord]):
    if "abs_url" in df.columns and "pdf_url" in df.columns:
        return df

    by_paper_id = {record.paper_id: record for record in records}
    if "abs_url" not in df.columns:
        df["abs_url"] = df["paper_id"].map(lambda paper_id: by_paper_id.get(paper_id).abs_url if by_paper_id.get(paper_id) else "")
    if "pdf_url" not in df.columns:
        df["pdf_url"] = df["paper_id"].map(lambda paper_id: by_paper_id.get(paper_id).pdf_url if by_paper_id.get(paper_id) else "")
    return df


def _load_or_build_testset(settings, df):
    test_set_path = settings.paths.eval_testset
    should_build = settings.refresh_test_set or not test_set_path.exists()
    if should_build:
        return build_test_set(df=df, output_path=test_set_path)
    return read_json(test_set_path)


def _source_summary(settings, records: list[PaperRecord], clean_df, test_set_size: int) -> dict[str, str | int]:
    return {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_records": len(records),
        "clean_rows": int(len(clean_df)),
        "test_samples": test_set_size,
        "raw_records_path": str(settings.paths.raw_records_json),
        "clean_csv_path": str(settings.paths.clean_csv),
        "clean_json_path": str(settings.paths.clean_json),
        "test_set_path": str(settings.paths.eval_testset),
        "metrics_path": str(settings.paths.baseline_metrics),
    }


def main() -> None:
    settings = load_settings()

    # 1-2) Source ingest: reuse cached raw records unless refresh is requested.
    records = _load_or_fetch_raw_records(settings)

    # 3-4) Clean and persist clean artifacts.
    clean_df = build_clean_dataframe(records=records, run_date=now_utc())
    clean_df = _ensure_index_columns(clean_df, records)
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    # 5) Build embedding index and store manifest.
    index = LocalEmbeddingIndex.build(
        df=clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    # 6) Build/load frozen test set.
    test_set = _load_or_build_testset(settings, clean_df)

    # 7) Run baseline evaluation metrics.
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    # 8) Quality and freshness checks.
    quality = run_data_quality_checks(clean_df, settings=settings, report_name="phase1_quality")
    freshness = build_freshness_report(clean_df, settings=settings, report_path=settings.paths.freshness_report)

    # 9) Markdown report.
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=_source_summary(settings, records, clean_df, len(test_set)),
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )


if __name__ == "__main__":
    main()
