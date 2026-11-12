"""Shared UTC evaluation windows for the Precinct6 signal capture."""

import pandas as pd

TRAIN_END_UTC = "2024-07-29T00:00:00Z"
TEST_END_UTC = "2024-07-31T00:00:00Z"
DRIFT_END_UTC = "2024-08-02T00:00:00Z"
TRAIN_END = pd.Timestamp(TRAIN_END_UTC).timestamp()
TEST_END = pd.Timestamp(TEST_END_UTC).timestamp()
DRIFT_END = pd.Timestamp(DRIFT_END_UTC).timestamp()
WINDOW_LABELS = {
    "train": f"timestamp < {TRAIN_END_UTC}",
    "test": f"[{TRAIN_END_UTC}, {TEST_END_UTC})",
    "drift": f"[{TEST_END_UTC}, {DRIFT_END_UTC})",
}


def temporal_windows(df: pd.DataFrame, timestamp_col: str = "timestamp"):
    """Return train, main test, and later drift slices without sampling rows."""
    if timestamp_col not in df.columns:
        raise ValueError(f"missing timestamp column: {timestamp_col}")
    timestamps = df[timestamp_col]
    if not pd.api.types.is_numeric_dtype(timestamps):
        raise TypeError(f"{timestamp_col} must contain Unix timestamps in seconds")

    return (
        df.loc[timestamps < TRAIN_END].copy(),
        df.loc[(timestamps >= TRAIN_END) & (timestamps < TEST_END)].copy(),
        df.loc[(timestamps >= TEST_END) & (timestamps < DRIFT_END)].copy(),
    )


def population_summary(df: pd.DataFrame, label_col: str = "label_binary"):
    """Summarize every row in an evaluation window without rebalancing it."""
    if label_col not in df.columns:
        raise ValueError(f"missing label column: {label_col}")
    counts = df[label_col].value_counts(dropna=False)
    total = len(df)
    class_counts = {str(label): int(count) for label, count in counts.items()}
    prevalence = {
        label: round(count / total, 6) if total else 0.0
        for label, count in class_counts.items()
    }
    return {"n": total, "class_counts": class_counts, "prevalence": prevalence}
