from __future__ import annotations

from pathlib import Path

from services.symbolic.pipeline import load_symbolic_dataset, run_symbolic_pipeline


def run_symbolic_pipeline(csv_path: Path | str) -> dict[str, object]:
    csv_path = Path(csv_path)
    df = load_symbolic_dataset(csv_path)
    symbolic_output = run_symbolic_pipeline(df)
    return {
        "symbolic": {
            "patient_count": symbolic_output.get("patient_count", 0),
            "phenotypes": symbolic_output.get("patient_summary", {}).to_dict(orient="records") if "patient_summary" in symbolic_output else symbolic_output,
        },
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run symbolic hypertension pipeline.")
    parser.add_argument("--csv", type=str, default="data/hypertension_dataset.csv")
    args = parser.parse_args()

    output = run_symbolic_pipeline(args.csv)
    print("Symbolic patient summary count:", output["symbolic"]["patient_count"])


if __name__ == "__main__":
    main()
