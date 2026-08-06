import json
from pathlib import Path
from src.ingestion.cleaning import clean_records
from src.evaluation.testset import create_test_set

def test_clean_records_example():
    # Load a small fixture (provide a tiny raw JSON fixture in tests/fixtures)
    raw = json.loads(Path('tests/fixtures/raw_sample.json').read_text())
    cleaned = clean_records(raw)
    assert cleaned  # basic sanity check
    # Ensure required fields exist
    for rec in cleaned:
        assert 'text_for_embedding' in rec
        assert rec['age_days'] >= 0

def test_create_test_set_example():
    cleaned = json.loads(Path('tests/fixtures/cleaned_sample.json').read_text())
    testset = create_test_set(cleaned, n_samples=5)
    assert len(testset) == 5
    for item in testset:
        assert 'question' in item
        assert 'ground_truth' in item
        assert 'ground_truth_doc_ids' in item
