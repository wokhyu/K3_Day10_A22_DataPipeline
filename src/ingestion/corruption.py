from __future__ import annotations

import random
from datetime import datetime, timedelta
import json
from pathlib import Path

import pandas as pd


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate data corruption based on the lab requirements."""
    # Create a copy so we don't modify the baseline dataframe in-place
    corrupted_df = df.copy()
    num_rows = len(corrupted_df)
    log_entries = []

    # Prepare random seed for reproducibility
    random.seed(42)

    # 1. Drop a some latest records (e.g. drop top 2 rows if sorted by date, or 5%)
    rows_to_drop = max(1, int(num_rows * 0.05))
    corrupted_df = corrupted_df.iloc[rows_to_drop:].copy()
    log_entries.append({"type": "drop", "count": rows_to_drop, "description": "Dropped latest records"})

    # 2. Blank summary on some rows (10%)
    summary_blank_indices = random.sample(range(len(corrupted_df)), max(1, int(len(corrupted_df) * 0.1)))
    corrupted_df.iloc[summary_blank_indices, corrupted_df.columns.get_loc('summary')] = ""
    log_entries.append({"type": "blank_summary", "count": len(summary_blank_indices), "description": "Blanked out summaries"})

    # 3. Inject noise into text (10% of titles)
    noise_chars = "!@#$%"
    noise_indices = random.sample(range(len(corrupted_df)), max(1, int(len(corrupted_df) * 0.1)))
    for idx in noise_indices:
        title = corrupted_df.iloc[idx]['title']
        if title:
            pos = random.randint(0, len(title) - 1)
            new_title = title[:pos] + random.choice(noise_chars) + title[pos+1:]
            corrupted_df.iloc[idx, corrupted_df.columns.get_loc('title')] = new_title
    log_entries.append({"type": "inject_noise", "count": len(noise_indices), "description": "Injected noise into titles"})

    # 4. Make title truncated (10%)
    truncate_indices = random.sample(range(len(corrupted_df)), max(1, int(len(corrupted_df) * 0.1)))
    for idx in truncate_indices:
        title = corrupted_df.iloc[idx]['title']
        if title and len(title) > 10:
            corrupted_df.iloc[idx, corrupted_df.columns.get_loc('title')] = title[:10] + "..."
    log_entries.append({"type": "truncate_title", "count": len(truncate_indices), "description": "Truncated titles"})

    # 5. Make published date older (e.g. minus 5 years for 10% of rows)
    stale_indices = random.sample(range(len(corrupted_df)), max(1, int(len(corrupted_df) * 0.1)))
    for idx in stale_indices:
        pub = corrupted_df.iloc[idx]['published']
        if pub:
            try:
                pub_dt = pd.to_datetime(pub)
                old_dt = pub_dt - timedelta(days=1825)
                corrupted_df.iloc[idx, corrupted_df.columns.get_loc('published')] = old_dt.isoformat()
                if 'age_days' in corrupted_df.columns and pd.notna(corrupted_df.iloc[idx]['age_days']):
                    corrupted_df.iloc[idx, corrupted_df.columns.get_loc('age_days')] += 1825
            except Exception:
                pass
    log_entries.append({"type": "stale_date", "count": len(stale_indices), "description": "Made published dates older"})

    # 6. Add duplicate rows
    if len(corrupted_df) > 0:
        duplicates = corrupted_df.sample(n=min(2, len(corrupted_df)), random_state=42)
        corrupted_df = pd.concat([corrupted_df, duplicates], ignore_index=True)
        log_entries.append({"type": "duplicate_rows", "count": len(duplicates), "description": "Added duplicate rows"})

    # 7. Rebuild `text_for_embedding`
    def build_embedding_text(row):
        title = str(row.get('title', ''))
        summary = str(row.get('summary', ''))
        authors = str(row.get('authors_joined', ''))
        return f"{title}\n{summary}\n{authors}"
        
    corrupted_df['text_for_embedding'] = corrupted_df.apply(build_embedding_text, axis=1)

    # 8. Ghi corruption log vao output_log_path
    output_path = Path(output_log_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(log_entries, f, indent=2)

    return corrupted_df
