# Phase 1 Report

## Source Summary

- **source_api**: Crossref REST API
- **source_query**: agentic retrieval augmented generation large language model
- **source_filter**: from-pub-date:2026-02-07,has-abstract:true
- **raw_records**: 24
- **clean_rows**: 24
- **test_samples**: 72
- **raw_records_path**: D:\AI thực chiến\Lab\DAY10_2A202601627_NguyenQuocHieu\data\raw\crossref_records.json
- **clean_csv_path**: D:\AI thực chiến\Lab\DAY10_2A202601627_NguyenQuocHieu\data\clean\papers_clean.csv
- **clean_json_path**: D:\AI thực chiến\Lab\DAY10_2A202601627_NguyenQuocHieu\data\clean\papers_clean.json
- **test_set_path**: D:\AI thực chiến\Lab\DAY10_2A202601627_NguyenQuocHieu\data\eval\test_set.json
- **metrics_path**: D:\AI thực chiến\Lab\DAY10_2A202601627_NguyenQuocHieu\data\results\baseline_metrics.json

## Evaluation Metrics

- **samples**: 72
- **retrieval_hit_rate**: 1.0
- **mean_token_f1**: 0.7568269675884299
- **judge_accuracy**: 0.6944444444444444
- **mean_judge_score**: 3.9583333333333335
- **ragas**: {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}

## Data Quality

- **report_name**: phase1_quality
- **total_rows**: 24
- **missing_paper_id**: 0
- **duplicate_paper_id**: 0
- **missing_title**: 0
- **empty_summary**: 0
- **stale_rows**: 0
- **passed**: True

## Freshness

- **latest_published**: 2026-08-01T00:00:00+00:00
- **oldest_published**: 2026-02-12T00:00:00+00:00
- **stale_rows**: 0
- **total_rows**: 24
- **is_fresh**: True
