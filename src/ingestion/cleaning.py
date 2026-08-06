from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw ``PaperRecord`` objects and return a ready‑to‑embed DataFrame.

    The cleaning pipeline follows the lab specification:
    * Normalise textual fields (strip whitespace, collapse multiple spaces).
    * Join list fields (authors, categories) into a single string.
    * Parse the ``published`` date and compute ``age_days`` relative to *run_date*.
    * Build a ``text_for_embedding`` column that concatenates title, summary and authors.
    * Drop records that are obviously bad (empty title/summary, very short title).
    * Remove duplicate records based on ``paper_id``.
    * Return the DataFrame sorted by ``published`` descending.
    """
    # Helper to safely clean a string
    def _clean_text(value: str) -> str:
        return " ".join(value.strip().split()) if isinstance(value, str) else ""

    rows = []
    for rec in records:
        # Required fields must be present
        if not rec.paper_id or not rec.title or not rec.summary:
            continue
        # Basic length checks
        if len(_clean_text(rec.title)) < 5:
            continue
        # Normalise fields
        title = _clean_text(rec.title)
        summary = _clean_text(rec.summary)
        authors = ", ".join([_clean_text(a) for a in rec.authors if a])
        categories = ", ".join([_clean_text(c) for c in rec.categories if c])
        # Parse published date – fallback to empty string
        try:
            published_dt = pd.to_datetime(rec.published, utc=True).to_pydatetime()
        except Exception:
            published_dt = None
        # Compute age in days relative to run_date
        age_days = (run_date - published_dt).days if published_dt else None
        # Build embedding text
        text_for_embedding = f"{title}\n{summary}\n{authors}"
        rows.append({
            "paper_id": rec.paper_id,
            "title": title,
            "summary": summary,
            "authors_joined": authors,
            "categories_joined": categories,
            "published": rec.published,
            "age_days": age_days,
            "text_for_embedding": text_for_embedding,
        })

    if not rows:
        raise ValueError("No valid records after cleaning.")

    df = pd.DataFrame(rows)
    # Drop duplicate paper_id if any
    df = df.drop_duplicates(subset="paper_id", keep="first")
    # Sort by published date descending (most recent first)
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    return df
