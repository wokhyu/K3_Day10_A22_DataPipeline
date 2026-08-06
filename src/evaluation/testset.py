from __future__ import annotations

from typing import Any

import pandas as pd


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
        # Prepare a few generic question types
        q_types = {
            "summary": f"What is the main contribution of the paper titled '{row['title']}'?",
            "authors": f"Who are the authors of the paper titled '{row['title']}'?",
            "date": f"When was the paper titled '{row['title']}' published?",
            "categories": f"What topics does the paper titled '{row['title']}' cover?",
        }
        for q_type, question in q_types.items():
            ground_truth = None
            if q_type == "summary":
                ground_truth = row["summary"]
            elif q_type == "authors":
                ground_truth = row["authors_joined"]
            elif q_type == "date":
                ground_truth = row["published"]
            elif q_type == "categories":
                ground_truth = row["categories_joined"]
            test_items.append({
                "id": f"{doc_id}_{q_type}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": doc_id,
            })

    # Write JSON file
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    with output_path_obj.open("w", encoding="utf-8") as f:
        json.dump(test_items, f, ensure_ascii=False, indent=2)

    return test_items
