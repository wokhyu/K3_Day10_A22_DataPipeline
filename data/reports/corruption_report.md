# Corruption Comparison Report

## Summary

This report compares the baseline, corrupted, and repaired datasets for retrieval and data quality performance.

## Baseline Metrics

- **samples**: 72
- **retrieval_hit_rate**: 1.0
- **mean_token_f1**: 0.7568269675884299
- **judge_accuracy**: 0.6944444444444444
- **mean_judge_score**: 3.9583333333333335
- **ragas**: {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}

## Corrupted Metrics

- **samples**: 72
- **retrieval_hit_rate**: 0.9583333333333334
- **mean_token_f1**: 0.6895692312632726
- **judge_accuracy**: 0.6388888888888888
- **mean_judge_score**: 3.6944444444444446
- **ragas**: {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}

## Repaired Metrics

- **samples**: 72
- **retrieval_hit_rate**: 1.0
- **mean_token_f1**: 0.7568269675884299
- **judge_accuracy**: 0.6944444444444444
- **mean_judge_score**: 3.9583333333333335
- **ragas**: {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}

## Quality Comparison

- **Corrupted quality passed**: False
- **Repaired quality passed**: True

## Freshness Comparison

- **Corrupted freshness is_fresh**: False
- **Repaired freshness is_fresh**: True
