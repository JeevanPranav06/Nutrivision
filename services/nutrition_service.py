import os
import json
from typing import Dict, Any, Tuple
from difflib import get_close_matches

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATASET_PATH = os.path.join(DATA_DIR, "nutrition_dataset.json")

# Cache dataset in memory for performance
_DATASET: Dict[str, Dict[str, float]] | None = None


def _load_dataset() -> Dict[str, Dict[str, float]]:
    global _DATASET
    if _DATASET is not None:
        return _DATASET

    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            f"nutrition_dataset.json not found at {DATASET_PATH}. Please create it with realistic entries."
        )

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalize keys to lowercase for matching
    _DATASET = {k.lower(): v for k, v in data.items()}
    return _DATASET


def _normalize_query(query: str) -> str:
    return query.strip().lower()


def _best_match(query: str, dataset: Dict[str, Dict[str, float]]) -> Tuple[str | None, float]:
    """
    Returns (best_key, confidence_score)
    """
    keys = list(dataset.keys())
    matches = get_close_matches(query, keys, n=3, cutoff=0.5)

    if not matches:
        return None, 0.0

    best = matches[0]

    # crude confidence: ratio of matching characters
    score = len(set(best.split()) & set(query.split())) / max(len(best.split()), 1)
    return best, score


def get_nutrition(food_name: str) -> Dict[str, Any]:
    """
    Main API: returns nutrition for a detected food name.
    Applies fuzzy matching to find closest entry.
    """
    dataset = _load_dataset()
    query = _normalize_query(food_name)

    # Direct match
    if query in dataset:
        return {
            "name": query.title(),
            **dataset[query],
    _DATASET = None