import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from services.clinic_engine.stage1_measurement_classification.data.dataset import generate_synthetic_hypertension_data


def main() -> None:
    output_path = Path(__file__).resolve().parents[1] / "data" / "hypertension_dataset.csv"
    df = generate_synthetic_hypertension_data(output_path)
    print(f"Generated synthetic hypertension dataset with {len(df)} rows at: {output_path}")


if __name__ == "__main__":
    main()
