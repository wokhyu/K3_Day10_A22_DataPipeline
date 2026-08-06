from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv, write_json, now_utc
from evaluation.metrics import evaluate_pipeline
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

def _ensure_index_columns(df, records):
    if "abs_url" in df.columns and "pdf_url" in df.columns:
        return df

    by_paper_id = {record.paper_id: record for record in records}
    if "abs_url" not in df.columns:
        df["abs_url"] = df["paper_id"].map(lambda paper_id: by_paper_id.get(paper_id).abs_url if by_paper_id.get(paper_id) else "")
    if "pdf_url" not in df.columns:
        df["pdf_url"] = df["paper_id"].map(lambda paper_id: by_paper_id.get(paper_id).pdf_url if by_paper_id.get(paper_id) else "")
    return df


def main() -> None:
    settings = load_settings()

    # 1. Load baseline metrics va clean dataset
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.DataFrame(read_json(settings.paths.clean_json))

    # 2. Tao corrupted dataframe
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)

    # 3. Save corrupted artifacts
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    # 4. Rebuild index va evaluate for corrupted data
    corrupted_index = LocalEmbeddingIndex.build(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    corrupted_evaluation = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )

    # 5. Run quality checks/freshness tren corrupted data
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness.json")

    # 6. Repair lai tu raw records
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(records=raw_records, run_date=now_utc())
    repaired_df = _ensure_index_columns(repaired_df, raw_records)
    
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))

    # 7. Evaluate repaired dataset
    repaired_index = LocalEmbeddingIndex.build(
        df=repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_evaluation = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(repaired_df, settings, settings.paths.quality_dir / "repaired_freshness.json")

    # 8. Tao comparison report
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )


if __name__ == "__main__":
    main()
