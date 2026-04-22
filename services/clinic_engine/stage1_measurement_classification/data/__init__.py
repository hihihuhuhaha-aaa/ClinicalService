"""Data layer: synthetic data generation and dataset loading."""

from .dataset import generate_synthetic_hypertension_data, load_hypertension_data

__all__ = [
    "generate_synthetic_hypertension_data",
    "load_hypertension_data",
]
