from __future__ import annotations

from typing import Any

import pandas as pd


def _as_ground_truth(value: Any) -> str:
    """Return *value* as a trimmed string, or ``""`` when it is missing."""
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).split())


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create an evaluation test‑set from a cleaned DataFrame.

    The function follows the lab's pseudo‑code:
    1. Verify that the DataFrame contains at least one document.
    2. Randomly sample up to 30 records (or all if fewer).
    3. For each sampled record generate several question types – summary,
       authors, date and categories.
    4. Each row of the test‑set includes the required fields:
       ``id``, ``question_type``, ``question``, ``ground_truth`` and
       ``ground_truth_doc_ids``.
    5. The resulting list is written to *output_path* as JSON and also
       returned.
    """
    import json
    import random
    from pathlib import Path

    if df.empty:
        raise ValueError("Cleaned DataFrame is empty – cannot build a test set.")

    # Determine how many samples to draw (max 30 as a reasonable default)
    n_samples = min(30, len(df))
    sampled = df.sample(n=n_samples, random_state=42)

    test_items: list[dict[str, Any]] = []
    for _, row in sampled.iterrows():
        doc_id = row["paper_id"]
        # Prepare a few generic question types, each with its ground truth column
        q_types = {
            "summary": (
                f"What is the main contribution of the paper titled '{row['title']}'?",
                row["summary"],
            ),
            # The phrasing below is deliberate: retrieval/qa.py routes a question
            # to the right metadata field by matching these intent phrases, so a
            # reworded question would silently fall back to the summary branch.
            "authors": (
                f"Who authored the paper titled '{row['title']}'?",
                row["authors_joined"],
            ),
            "date": (
                f"When was the paper titled '{row['title']}' published?",
                row["published"],
            ),
            "categories": (
                f"What categories does the paper titled '{row['title']}' cover?",
                row["categories_joined"],
            ),
        }
        for q_type, (question, raw_ground_truth) in q_types.items():
            ground_truth = _as_ground_truth(raw_ground_truth)
            if not ground_truth:
                # A missing ground truth cannot be scored – skip it rather than
                # writing NaN into the frozen test set.
                continue
            test_items.append({
                "id": f"{doc_id}_{q_type}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [doc_id],
            })

    if not test_items:
        raise ValueError("No test items could be built – every ground truth was empty.")

    # Write JSON file
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    with output_path_obj.open("w", encoding="utf-8") as f:
        json.dump(test_items, f, ensure_ascii=False, indent=2)

    return test_items
